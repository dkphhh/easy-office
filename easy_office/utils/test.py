import asyncio
import base64
import csv
import os
from pathlib import Path

import httpx
from aiolimiter import AsyncLimiter
from dotenv import load_dotenv

load_dotenv()

rate_limit = AsyncLimiter(5, 1)


API_KEY = os.getenv("BAIDU_API_KEY")
SECRET_KEY = os.getenv("BAIDU_SECRET_KEY")


async def request_invoice_api(path: Path):
    async with rate_limit:
        async with httpx.AsyncClient() as client:
            # ---------获取token-----------

            token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"

            token_payload = ""
            token_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            token_res = await client.post(
                token_url,
                json=token_payload,
                headers=token_headers,
            )

            token = token_res.json()["access_token"]

            vat_invoice_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={token}"

            request_headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            upload_data = path.read_bytes()

            file_b64 = base64.b64encode(upload_data).decode(
                "utf-8"
            )

            request_payload = {"pdf_file": file_b64}

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
                "file_name": path.name,  # 文件名
                "amount_in_figuers": words_result[
                    "AmountInFiguers"
                ],  # 价税合计(小写)
                "amount_in_words": words_result[
                    "AmountInWords"
                ],  # 价税合计(小写)
                "invoice_date": words_result[
                    "InvoiceDate"
                ],  # 开票日期
                "invoice_num": words_result[
                    "InvoiceNum"
                ],  # 发票号码
                "invoice_type": words_result[
                    "InvoiceType"
                ],  # 发票种类
                "purchaser_name": words_result[
                    "PurchaserName"
                ],  # 购买方姓名
                "purchaser_register_num": words_result[
                    "PurchaserRegisterNum"
                ],  # 购买方税号
                "seller_name": words_result[
                    "SellerName"
                ],  # 销售方姓名
                "seller_register_num": words_result[
                    "SellerRegisterNum"
                ],  # 销售方纳税人识别号
                "total_amount": words_result[
                    "TotalAmount"
                ],  # 合计金额
                "total_tax": words_result[
                    "TotalTax"
                ],  # 合计税额
            }

            return result


if __name__ == "__main__":
    
    path = "/Users/dkphhh/Downloads/邓鲲鹏报销"

    async def main(path: str):
        pdf_dir = Path(path)
        pdf_list = list(pdf_dir.rglob("*.pdf"))

        tasks = [
            request_invoice_api(pdf) for pdf in pdf_list
        ]

        data = await asyncio.gather(*tasks)

        with open(
            file=pdf_dir / "output.csv",
            mode="w",
            newline="",
            encoding="utf-8",
        ) as f:
            # 获取字段名（列名）
            fieldnames = data[0].keys()

            # 创建 CSV writer 对象
            writer = csv.DictWriter(
                f, fieldnames=fieldnames
            )

            # 写入表头
            writer.writeheader()

            # 写入数据行
            writer.writerows(data)

    asyncio.run(main(path=path))
