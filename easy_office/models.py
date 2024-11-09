from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

import reflex as rx
from sqlmodel import Field, select



class JournalAccount(rx.Model, table=True):
    id: Annotated[int | None, Field(primary_key=True)] = None
    trade_date: Annotated[date, Field(index=True)] = (
        datetime.now().date()
    )  # 交易发生的日期
    description: Annotated[str, Field(index=True, max_length=1000)] = (
        ""  # 关于这笔流水的说明
    )
    additional_info: Annotated[str, Field(index=True, max_length=1000)] = ""  # 备注
    amount: Annotated[Decimal, Field(decimal_places=2)] = Decimal("0")  # 金额
    category: Annotated[str, Field(index=True, max_length=255)] = ""  # 分类
    payer: Annotated[str, Field(index=True, max_length=255)] = ""  # 付款方
    receiver: Annotated[str, Field(index=True, max_length=255)] = ""  # 收款方
    bank_slip_url: str = ""  # 银行回单文件链接
    tax_invoice_url: str = ""  # 发票文件链接
    created_datetime: datetime = datetime.now()  # 记录生成时间

    @classmethod
    def create_empty_record(cls) -> "JournalAccount":
        with rx.session() as session:
            new_record = JournalAccount()
            session.add(new_record)
            session.commit()

            return new_record

    @classmethod
    def create_records(cls, records: list[dict]) -> list["JournalAccount"]:
        with rx.session() as session:
            new_records = []

            for record in records:

                print(
                    f"""record["amount"]:{record["amount"]} is {type(record["amount"])}"""
                )

                if isinstance(record["amount"], str):
                    record["amount"] = Decimal(record["amount"])

                    print(
                        f"""此时，record["amount"]：{record["amount"]} is {type(record["amount"])}"""
                    )

                new_record = JournalAccount(**record)
                new_records.append(new_record)
                session.add(new_record)

            session.commit()

            for record in new_records:
                session.refresh(record)

            return new_records

    @classmethod
    def get_all_records(cls) -> list[dict]:
        with rx.session() as session:
            records = session.exec(select(JournalAccount)).all()
            result = [record.model_dump() for record in records]
            return result


if __name__ == "__main__":
    pass
