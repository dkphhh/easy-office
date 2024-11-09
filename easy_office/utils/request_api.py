import asyncio
import base64
import os
import random
import re
import string
import time
from datetime import date, datetime
from typing import Literal

import httpx
import reflex as rx

from .log import logger

# 从环境变量中获取密钥参数
API_KEY = os.getenv("APIKEY")
SECRET_KEY = os.getenv("SECRETKEY")
BACK_END = os.getenv("BACK_END")


DATE_TO_REMOVE = "-/\\.:：年月日时秒分 "
AMOUNT_PATTERN = re.compile(r"[^\d.]")


# ================  请求百度 ocr api ====================


def recognize_filetype(file: rx.UploadFile) -> tuple[str, str]:
    """
    检查用户上传的文件是图片还是pdf,并返回文件类型和扩展名
    Args:
        file:用户上传的文件
    Returns: 返回一个元组 (文件类型,扩展名)

    """
    filename = file.filename.lower()  # type: ignore
    image_extensions = (".jpg", ".jpeg", ".png", ".bmp")
    file_extension = (
        "." + filename.split(".")[-1] if "." in filename else ""
    )  # 获取文件扩展名

    # 判断文件类型
    if file_extension in image_extensions:
        return "img", file_extension
    elif file_extension == ".pdf":
        return "pdf", file_extension
    else:
        raise TypeError("未知文件类型")


def generate_random_string(length: int = 12) -> str:
    """生成指定长度的随机字符串"""
    # 定义字符池
    characters = string.ascii_letters + string.digits  # 包含大小写字母和数字
    return "".join(random.choice(characters) for _ in range(length))


def generate_filename(file_extension: str, length=6) -> str:
    """生成随机字符串,格式：时间+6位随机字符
    Args:
        file_extension：文件扩展名
        length: 字符串长度
    """
    characters = string.ascii_letters + string.digits
    random_string = "".join(random.choice(characters) for _ in range(length))
    new_file_name = (
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random_string}{file_extension}"
    )
    return new_file_name


def parse_date(date_string: str) -> date | str:
    """将银行回单内的日期时间字符串转化为 datetime 格式
    简单来说，就是把 DATE_TO_REMOVE 里的所有字符全部删除
    然后转化为 date 格式

    Args:
        date_string (str): 日期格式的字符串

    Returns:
         date | str: date 对象或者空字符串 ""
    """
    try:
        trans_table = str.maketrans("", "", DATE_TO_REMOVE)
        date_num = date_string.translate(trans_table)
        result = date.fromisoformat(date_num)
        return result
    except (ValueError, TypeError):
        logger.error(f"输入的 date_string 为:{date_string},无法正常完成解析")
        result = ""

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
        logger.error(f"输入的 amount_str 为:{amount_str},无法正常完成解析")
        result = ""

        return result


def process_bank_slip(words_result: dict) -> dict:
    trade_date = parse_date(words_result["交易日期"][0]["word"])
    amount = extract_amount(words_result["小写金额"][0]["word"])
    payer = words_result["付款人户名"][0]["word"]
    receiver = words_result["收款人户名"][0]["word"]

    return {
        "trade_date": trade_date,
        "amount": amount,
        "payer": payer,
        "receiver": receiver,
    }


async def request_baidu_ocr(
    file: rx.UploadFile, mode: Literal["bank_slip", "vat_invoice"]
) -> dict | None:
    """
    想百度api发出请求，将文件（图片/pdf）上传，根据模式不同上传到不同的 api 接口
    Args:
        file: 用户上传的 文件（图片/pdf）
        mode: 识别模式，目前支持两种模式，银行回单识别（bank_slip）或增值税发票识别（vat_invoice）

    Returns:
        返回识别结果的字典。

    """

    async with httpx.AsyncClient() as client:
        # ---------获取token-----------

        task_id = generate_random_string()  # 用于记录运行日志

        logger.info(f"开始执行任务，task_id：{task_id}")

        token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"

        token_payload = ""
        token_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            token_res = await client.post(
                token_url, json=token_payload, headers=token_headers
            )

            token = token_res.json()["access_token"]

            # ----处理文件-------

            filetype, file_extension = recognize_filetype(
                file
            )  # 获取文件类型 和 文件扩展名

            new_filename = generate_filename(
                file_extension, length=6
            )  # 用时间和随机字符串给文件重新命名
            upload_file = (
                rx.get_upload_dir() / new_filename
            )  # 创建一个保存上传文件的地址

            # 默认保存文件的目录时 upload_files

            upload_data = await file.read()

            with upload_file.open("wb") as file_object:
                file_object.write(upload_data)  # 把文件保存到指定目录

            # 输出文件的 base64 字符串
            file_b64 = base64.b64encode(upload_data).decode("utf-8")

            # 请求api的参数
            request_headers = {"Content-Type": "application/x-www-form-urlencoded"}
            request_payload = (
                {"image": file_b64} if filetype == "img" else {"pdf_file": file_b64}
            )
        except Exception as e:

            logger.error(f"task_id:{task_id};准备阶段，运行时出现错误:{e}")
            raise (f"准备阶段，运行时出现错误:{e}")

        match mode:
            case "bank_slip":
                # ----------银行回单请求-------

                bank_slip_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/bank_receipt_new?access_token={token}"

                bank_slip_res = await client.post(
                    url=bank_slip_url, headers=request_headers, data=request_payload
                )

                bank_slip_result = bank_slip_res.json()

                logger.info(
                    f"task-id:{task_id};正在处理文件：{file.filename};API返回的银行回单信息：{bank_slip_result}"
                )

                words_result: dict = bank_slip_result["words_result"]

                # 校验api 回传数据是否都是空值
                validate_result = [i[0]["word"] for i in words_result.values()]
                if all(i == "" for i in validate_result):
                    logger.error(
                        f"task-id:{task_id};上传的文件：「{file.filename}」似乎不是银行回单"
                    )
                    raise ValueError(f"上传的文件「{file.filename}」似乎不是银行回单")

                result = process_bank_slip(words_result)

                result["bank_slip_url"] = f"{BACK_END}/_upload/{new_filename}"

                result["task_id"] = task_id

                logger.info(result)

                return result

            case "vat_invoice":
                # ------------发票请求-----------

                vat_invoice_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={token}"

                vat_invoice_res = await client.post(
                    url=vat_invoice_url, headers=request_headers, data=request_payload
                )

                vat_invoice_result = vat_invoice_res.json()

                words_result = vat_invoice_result["words_result"]

            case _:
                raise AttributeError("识别模式错误！")


# ================== 请求飞书多为表格 api =====================


async def create_new_record(record: dict):

    async with httpx.AsyncClient() as client:

        task_id = record.get("task_id", "")

        try:

            # --------- 获取token -------

            get_token_url = (
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            )

            get_token_header = {
                "Content-Type": "application/json;charset=utf-8",
            }

            get_token_body = {
                "app_id": "cli_a7a5d48eeab81013",
                "app_secret": "UHPs2ZgElNwadOaa0GXDsdQdnmorcKLV",
            }

            token_resp = await client.post(
                url=get_token_url, headers=get_token_header, json=get_token_body
            )

            token_resp = token_resp.json()

            tenant_access_token = token_resp["tenant_access_token"]

        except Exception as e:

            logger.error(f"task_id:{task_id};未能获取飞书 API 访问凭证，发生错误：{e}")

            raise (f"未能获取飞书 API 访问凭证，发生错误：{e}")

        # --------新增记录---------

        app_token = "MFoQbIqCNaujgzsn7vOcTfpBnjb"

        table_id = "tblrtFGd80L0Z0Hk"

        create_record_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"

        create_record_header = {
            "Authorization": f"Bearer {tenant_access_token}",
            "Content-Type": "application/json;charset=utf-8",
        }

        try:

            trade_date: date = record["trade_date"]
            # 飞书要求日期字段是毫秒级精度的 Unix 时间戳
            timestamp = int(time.mktime(trade_date.timetuple()) * 1000)

        except Exception as e:

            logger.error(f"task_id:{task_id};时间戳生成错误：{e}")

            raise (f"时间戳生成错误：{e}")

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
                "发票链接": record.get("tax_invoice_url", ""),
            },
        }

        logger.info(f"task_id:{task_id};准备发送到飞书文档的数据:{create_record_body}")

        create_record_resp = await client.post(
            url=create_record_url,
            headers=create_record_header,
            json=create_record_body,
        )

        create_record_resp = create_record_resp.json()

        code = create_record_resp.get("code")

        match code:

            case 0:
                logger.info(f"task_id:{task_id};成功上传到飞书文档。")

            case _:

                logger.error(
                    f"task_id:{task_id};未能成功上传数据到飞书文档，发生错误：{create_record_resp}"
                )
                raise Exception(
                    f"task_id:{task_id};未能成功上传数据到飞书文档，发生错误：{create_record_resp}"
                )


if __name__ == "__main__":
    record = {
        "trade_date": date.today(),
        "description": "这是描述",
        "additional_info": "",
        "amount": "123.60",
        "category": "",
        "payer": "测试付款方",
        "receiver": "测试收款方",
        "bank_slip_url": "http://101.201.153.207:8000/_upload/20241105203551-AJiWAH.pdf",
        "tax_invoice_url": "http://101.201.153.207:8000/_upload/20241105203551-AJiWAH.pdf",
    }

    resp = asyncio.run(create_new_record(record=record))

    print(resp)
