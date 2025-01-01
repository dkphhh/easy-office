import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

import reflex as rx
from reflex_ag_grid import ag_grid

from ..utils.file_process import (
    save_file_list,
)
from ..utils.request_api import (
    Request_Baidu_OCR,
    create_new_record,
)
from .components.check_password import check_password
from .components.template import page_template
from .components.upload_zone import upload_zone


class BankSlipState(rx.State):
    up_loading: bool = False
    upload_data: list[dict] = []

    @rx.var
    def data(self) -> list[dict]:
        """
        Ag Grid 组件最好用 computed var 传输数据，用 state var 数据更新会有延迟
        Returns: 用户上传的数据

        """
        return self.upload_data

    @rx.event
    async def upload_for_bank_slip_ocr(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator:
        """
        调用百度云的api，上传用户传入的文件，将返回的数据赋值给 self.upload_data
        Args:
            files: 用户上传的文件

        """
        self.up_loading = True  # 显示加载状态

        yield

        try:
            files_list = await save_file_list(files)
            tasks = [
                Request_Baidu_OCR(file=file).bank_slip()
                for file in files_list
            ]

            resp_list = await asyncio.gather(*tasks)

            self.upload_data.extend(resp_list)  # type:ignore

        except Exception as e:
            yield rx.toast.error(f"{e}", close_button=True)

        finally:
            self.up_loading = False

    @rx.event
    def cell_value_changed(
        self, row, col_field, new_value
    ) -> None:
        """
        同步更新表格
        Args:
            row: 更新表格的行数
            col_field:  更新表格的字段
            new_value: 用户输入的新值

        """

        if col_field == "trade_date":
            try:
                # 将 ISO 格式转换为 YYYY-MM-DD 格式
                utc_date = datetime.fromisoformat(
                    new_value.replace("Z", "+00:00")
                )
                local_date = utc_date + timedelta(hours=8)
                formatted_date = local_date.strftime(
                    "%Y-%m-%d"
                )
                self.upload_data[row][col_field] = (
                    formatted_date
                )

            except (
                ValueError,
                AttributeError,
            ):  # 如果没有收入值
                formatted_date = ""
                self.upload_data[row][col_field] = (
                    formatted_date
                )

        else:
            self.upload_data[row][col_field] = new_value

    @rx.event
    async def send_to_database(self):
        """
        将数据上传到数据库,刷新 upload_data，清空前端表格
        如果用户上传空数据会警告
        """
        try:
            if self.upload_data:
                self.up_loading = True

                yield

                tasks = [
                    create_new_record(record=record)
                    for record in self.upload_data
                ]

                await asyncio.gather(*tasks)

                # JournalAccount.create_records(records=self.upload_data)
                self.up_loading = False
                self.upload_data = []

            else:
                yield rx.toast.error(
                    "数据为空！", close_button=True
                )

        except Exception as e:
            yield rx.toast.error(f"{e}", close_button=True)


bank_slip_column_defs = [
    ag_grid.column_def(
        field="trade_date",
        header_name="交易日期",
        cell_data_type="date",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.date,
    ),
    ag_grid.column_def(
        field="description",
        header_name="项目描述",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        sortable=False,  # type:ignore
    ),
    ag_grid.column_def(
        field="additional_info",
        header_name="备注",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        sortable=False,  # type:ignore
    ),
    ag_grid.column_def(
        field="amount",
        header_name="金额",
        cell_data_type="number",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.number,
        sortable=False,  # type:ignore
    ),
    ag_grid.column_def(
        field="category",
        header_name="分类",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        cell_editor_params={
            "values": [
                "搜索广告",
                "营销推广",
                "外包劳务",
                "技术服务",
                "物业支出",
                "财务分红",
                "其他支出",
            ]
        },
        sortable=False,  # type:ignore
    ),
    ag_grid.column_def(
        field="payer",
        header_name="付款方",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        sortable=False,  # type:ignore
    ),
    ag_grid.column_def(
        field="receiver",
        header_name="收款方",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        sortable=False,  # type:ignore
    ),
    ag_grid.column_def(
        field="bank_slip_url",
        header_name="银行回单",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        sortable=False,  # type:ignore
    ),
]


def ag_grid_zone() -> rx.Component:
    return ag_grid(
        id="ag_grid_for_bank_slip",
        row_data=BankSlipState.data,
        column_defs=bank_slip_column_defs,
        on_cell_value_changed=BankSlipState.cell_value_changed,
        width="90vw",
        height="60vh",
    )


def send_records_button() -> rx.Component:
    return rx.button(
        "发送数据",
        on_click=BankSlipState.send_to_database,
        color=rx.color("slate", 2),
        bg=rx.color("slate", 12),
        loading=BankSlipState.up_loading,
    )


def bank_slip_ocr_page() -> rx.Component:
    return rx.el.div(
        upload_zone(
            loading=BankSlipState.up_loading,
            upload_handler=BankSlipState.upload_for_bank_slip_ocr(
                rx.upload_files(upload_id="upload1")  # type:ignore
            ),
        ),
        ag_grid_zone(),
        send_records_button(),
        class_name="flex flex-col items-center justify-center w-full space-y-2",
    )


meta = [
    {
        "name": "keywords",
        "content": "发票,银行回单,图片,PDF,识别,转Excel",
    }
]


@rx.page(
    route="/",
    title="快捷记账-EasyOffice",
    description="自动识别银行回单，并导入到数据库",
    meta=meta,
)
@check_password
def index() -> rx.Component:
    """主页面"""
    return page_template(
        bank_slip_ocr_page(),
    )
