import asyncio
import base64
import os
import re
import time
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from .file_process import (
    generate_random_string,
)
from .log import logger

# 从环境变量中获取密钥和参数
BAIDU_API_KEY: str | None = os.getenv("BAIDU_API_KEY")
BAIDU_SECRET_KEY: str | None = os.getenv("BAIDU_SECRET_KEY")
BACK_END: str | None = os.getenv("BACK_END")
DATE_TO_REMOVE = "-/\\.:：年月日时秒分 "
AMOUNT_PATTERN: re.Pattern[str] = re.compile(r"[^\d.]")
FEISHU_APP_ID: str | None = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET: str | None = os.getenv(
    "FEISHU_APP_SECRET"
)
FEISHU_APP_TOKEN: str | None = os.getenv("FEISHU_APP_TOKEN")
FEISHU_FINANCE_TABLE_ID: str | None = os.getenv(
    "FEISHU_FINANCE_TABLE_ID"
)

IMG_SUFFIX: list[str] = [".jpeg", ".jpg", ".png", ".bmp"]


class Token(ABC):
    token_duration: timedelta
    _token: str = ""
    _token_gen_datetime: datetime = datetime(
        year=2000,
        month=1,
        day=1,
    )  # 这个初始值没有意义，就是随便写一个以免报错

    @abstractmethod
    def gen_token(self) -> None:
        raise NotImplementedError

    @property
    def token(self) -> str:
        now = datetime.now()
        is_fresh = (
            (now - self._token_gen_datetime)
            < self.token_duration
        )  # 结果为真则有效期没过，结果未假则有效期过了

        if self._token and is_fresh:
            return self._token
        else:
            self.gen_token()
            return self._token


class BaiduToken(Token):
    token_duration: timedelta = timedelta(days=25)

    def __init__(
        self,
        url: str,
        headers: dict,
        payload: str = "",
    ) -> None:
        self.url = url
        self.headers = headers
        self.payload = payload

    def gen_token(self) -> None:
        token_res = httpx.post(
            url=self.url,
            json=self.payload,
            headers=self.headers,
        )

        token = token_res.json()["access_token"]
        self._token = token
        self._token_gen_datetime = datetime.now()


get_baidu_token = BaiduToken(
    url=f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}",
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
)


class FeishuToken(Token):
    token_duration: timedelta = timedelta(hours=1)

    def __init__(
        self,
        url: str,
        headers: dict,
        body: dict,
    ) -> None:
        self.url = url
        self.headers = headers
        self.body = body

    def gen_token(self) -> None:
        token_res: httpx.Response = httpx.post(
            url=self.url,
            headers=self.headers,
            json=self.body,
        )
        token = token_res.json()["tenant_access_token"]
        self._token = token
        self._token_gen_datetime = datetime.now()


get_feishu_token = FeishuToken(
    url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    headers={
        "Content-Type": "application/json;charset=utf-8",
    },
    body={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET,
    },
)

# ================  请求百度 ocr api ====================


def parse_date(date_string: str) -> date:
    """将银行回单内的日期时间字符串转化为 date 格式
    简单来说，就是把 DATE_TO_REMOVE 里的所有字符全部删除
    然后转化为 date 格式

    Args:
        date_string (str): 日期格式的字符串

    Returns:
        date : 如果能解析就解析，不能解析就输出当天日期
    """
    try:
        trans_table = str.maketrans("", "", DATE_TO_REMOVE)
        date_num = date_string.translate(trans_table)
        result = date.fromisoformat(date_num)
        return result
    except (ValueError, TypeError):
        logger.error(
            f"输入的 date_string 为:{date_string},无法正常完成解析"
        )
        result = date.today()

        return result


def extract_amount(amount_str: str) -> str:
    """将提取到的金额字符串转化为只包含数字和小数点的字符串

    Args:
        amount_str (str): 取到的金额字符串转

    Returns:
        str: 只包含数字和小数点的字符串
    """

    try:
        result = AMOUNT_PATTERN.sub("", amount_str)

        return result

    except (ValueError, TypeError):
        logger.error(
            f"输入的 amount_str 为:{amount_str},无法正常完成解析"
        )
        result = ""

        return result


def process_bank_slip(words_result: dict) -> dict:
    trade_date = parse_date(
        words_result["交易日期"][0]["word"]
    )
    amount = extract_amount(
        words_result["小写金额"][0]["word"]
    )
    payer = words_result["付款人户名"][0]["word"]
    receiver = words_result["收款人户名"][0]["word"]

    return {
        "trade_date": trade_date,
        "amount": amount,
        "payer": payer,
        "receiver": receiver,
    }


class Request_Baidu_OCR:
    def __init__(self, file: Path) -> None:
        self.file = file

    async def bank_slip(self) -> dict:
        token = get_baidu_token.token
        async with httpx.AsyncClient() as client:
            # ---------获取token-----------
            task_id = (
                generate_random_string()
            )  # 用于记录运行日志

            logger.info(
                f"开始执行任务，task_id：{task_id},任务类型:银行回单识别"
            )

            # ----处理文件-------

            # 输出文件的 base64 字符串
            file_b64 = base64.b64encode(
                self.file.read_bytes()
            ).decode("utf-8")

            # 请求api的参数
            request_headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            request_payload = (
                {"image": file_b64}
                if self.file.suffix in IMG_SUFFIX
                else {"pdf_file": file_b64}
            )

            print(request_payload.keys())

            # ----------银行回单请求-------

            bank_slip_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/bank_receipt_new?access_token={token}"

            bank_slip_res = await client.post(
                url=bank_slip_url,
                headers=request_headers,
                data=request_payload,
            )

            bank_slip_result = bank_slip_res.json()

            logger.info(
                f"task-id:{task_id};API返回的银行回单信息：{bank_slip_result}"
            )

            words_result: dict = bank_slip_result[
                "words_result"
            ]

            result = process_bank_slip(words_result)

            result["bank_slip_url"] = (
                f"{BACK_END}/_upload/{self.file.name}"
            )

            result["task_id"] = task_id

            logger.info(result)

            return result

    async def vat_invoice(self) -> dict:
        token = get_baidu_token.token
        async with httpx.AsyncClient() as client:
            task_id = (
                generate_random_string()
            )  # 用于记录运行日志

            logger.info(
                f"开始执行任务，task_id：{task_id},任务类型:发票识别"
            )

            vat_invoice_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={token}"

            request_headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            upload_data = self.file.read_bytes()

            file_b64 = base64.b64encode(upload_data).decode(
                "utf-8"
            )

            request_payload = (
                {"image": file_b64}
                if self.file.suffix in IMG_SUFFIX
                else {"pdf_file": file_b64}
            )
            vat_invoice_res = await client.post(
                url=vat_invoice_url,
                headers=request_headers,
                data=request_payload,
            )

            vat_invoice_result = vat_invoice_res.json()

            words_result: dict = vat_invoice_result[
                "words_result"
            ]

            result = {
                # "file_name": self.file.name,  # 文件名 -
                "invoice_date": words_result[
                    "InvoiceDate"
                ],  # 开票日期 -
                "invoice_num": words_result[
                    "InvoiceNum"
                ],  # 发票号码 -
                "invoice_type": words_result[
                    "InvoiceType"
                ],  # 发票种类 -
                "purchaser_name": words_result[
                    "PurchaserName"
                ],  # 购买方姓名 -
                "purchaser_register_num": words_result[
                    "PurchaserRegisterNum"
                ],  # 购买方税号 -
                "seller_name": words_result[
                    "SellerName"
                ],  # 销售方姓名 -
                "seller_register_num": words_result[
                    "SellerRegisterNum"
                ],  # 销售方纳税人识别号 -
                # "total_amount": words_result[
                #     "TotalAmount"
                # ],  # 合计金额
                # "total_tax": words_result[
                #     "TotalTax"
                # ],  # 合计税额
                "amount_in_figures": words_result[
                    "AmountInFiguers"
                ],  # 价税合计(小写)
                # "amount_in_words": words_result[
                #     "AmountInWords"
                # ],  # 价税合计(大写)
            }

            return result


# ================== 请求飞书多为表格 api =====================


async def create_new_record(record: dict):
    token = get_feishu_token.token
    async with httpx.AsyncClient() as client:
        task_id = record.get("task_id", "")

        # --------新增记录---------

        create_record_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_FINANCE_TABLE_ID}/records"

        create_record_header = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json;charset=utf-8",
        }

        try:
            trade_date: date = record["trade_date"]
            # 飞书要求日期字段是毫秒级精度的 Unix 时间戳
            timestamp = int(
                time.mktime(trade_date.timetuple()) * 1000
            )

        except Exception as e:
            logger.error(
                f"task_id:{task_id};时间戳生成错误：{e}"
            )

            raise Exception(f"时间戳生成错误：{e}")

        create_record_body = {
            "fields": {
                "交易日期": timestamp,
                "描述": record.get("description", ""),
                "备注": record.get("additional_info", ""),
                "金额": float(record.get("amount", 0)),
                "分类": record.get("category", ""),
                "付款方": record.get("payer", ""),
                "收款方": record.get("receiver", ""),
                "回单链接": record.get("bank_slip_url", ""),
            },
        }

        logger.info(
            f"task_id:{task_id};准备发送到飞书文档的数据:{create_record_body}"
        )

        create_record_resp = await client.post(
            url=create_record_url,
            headers=create_record_header,
            json=create_record_body,
        )

        create_record_resp = create_record_resp.json()

        code = create_record_resp.get("code")

        match code:
            case 0:
                logger.info(
                    f"task_id:{task_id};成功上传到飞书文档。"
                )

            case _:
                logger.error(
                    f"task_id:{task_id};未能成功上传数据到飞书文档，发生错误：{create_record_resp}"
                )
                raise Exception(
                    f"task_id:{task_id};未能成功上传数据到飞书文档，发生错误：{create_record_resp}"
                )


if __name__ == "__main__":
    ocr = Request_Baidu_OCR(
        file=Path(
            "/Users/dkphhh/Downloads/邓鲲鹏报销/24117000000900910420.pdf"
        )
    )

    result = asyncio.run(ocr.vat_invoice())

    print(result)
