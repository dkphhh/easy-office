import asyncio
import csv
from io import StringIO
from pathlib import Path

import reflex as rx
from reflex_ag_grid import ag_grid

from ..utils.file_process import (
    generate_filename,
    save_file_list,
)
from ..utils.request_api import Request_Baidu_OCR
from .components.check_password import check_password
from .components.template import page_template
from .components.upload_zone import upload_zone

CSV_HEADER = [
    "文件名",
    "开票日期",
    "发票号码",
    "发票种类",
    "购买方名称",
    "购买方税号",
    "销售方名称",
    "销售方税号",
    "价税合计",
]


class VatInvoiceState(rx.State):
    up_loading: bool = False
    upload_data: list[dict] = []

    @rx.var
    def data(self) -> list[dict]:
        """
        Ag Grid 组件最好用 computed var 传输数据，用 state var 数据更新会有延迟
        Returns: 用户上传的数据

        """
        return self.upload_data

    async def upload_for_vat_invoice(
        self, files: list[rx.UploadFile]
    ):
        """
        调用百度云的api，上传用户传入的文件，将返回的数据赋值给 self.upload_data
        Args:
            files: 用户上传的文件

        """
        self.up_loading = True  # 提示用户，程序开始运行

        yield

        try:
            files_list = await save_file_list(files)
            
            
            tasks = [
                Request_Baidu_OCR(file=file).vat_invoice()
                for file in files_list
            ]

          

            resp_list = await asyncio.gather(*tasks)
            
            # 生成原始的文件名
            file_name_list = [
                file.filename for file in files
            ]

            # 将原始文件名插入数据中
            invoice_data = [
                {"file_name": file_name.strip("./"), **data}  # type:ignore
                for data, file_name in zip(
                    resp_list, file_name_list
                )
            ]

            self.upload_data.extend(invoice_data)  # type:ignore

            yield

            # 识别完成后，删除所有上传的文件
            # map 返回的是一个生成器，不会立即执行删除，所以需要 list()
            list(map(Path.unlink, files_list))

        except Exception as e:
            yield rx.toast.error(f"{e}", close_button=True)

        finally:
            self.up_loading = (
                False  # 提示用户，运行状态结束
            )

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

        self.upload_data[row][col_field] = new_value

    @rx.event
    def download_result(self):
        self.up_loading = True

        yield

        csv_io = StringIO()
        writer = csv.writer(csv_io)
        writer.writerow(CSV_HEADER)
        rows = [row.values() for row in self.upload_data]
        writer.writerows(rows)
        csv_data = csv_io.getvalue()
        filename = generate_filename(file_extension=".csv")
        self.up_loading = False
        yield
        yield rx.download(data=csv_data, filename=filename)


vat_invoice_column_defs = [
    ag_grid.column_def(
        field="file_name",
        header_name="文件名",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="invoice_date",
        header_name="开票日期",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="invoice_num",
        header_name="发票号码",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="invoice_type",
        header_name="发票种类",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="purchaser_name",
        header_name="购买方名称",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="purchaser_register_num",
        header_name="购买方税号",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="seller_name",
        header_name="销售方名称",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="seller_register_num",
        header_name="销售方税号",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
    ag_grid.column_def(
        field="amount_in_figures",
        header_name="价税合计",
        cell_data_type="text",
        editable=True,
        sortable=False,  # type:ignore
        filter=None,
        cell_editor=ag_grid.editors.text,
    ),
]


def ag_grid_zone() -> rx.Component:
    return ag_grid(
        id="ag_grid_for_vat_invoice",
        row_data=VatInvoiceState.data,
        column_defs=vat_invoice_column_defs,
        on_cell_value_changed=VatInvoiceState.cell_value_changed,
        width="90vw",
        height="60vh",
    )


def download_result_button() -> rx.Component:
    return rx.button(
        "下载表格",
        on_click=VatInvoiceState.download_result,
        color=rx.color("slate", 2),
        bg=rx.color("slate", 12),
        loading=VatInvoiceState.up_loading,
    )


@rx.page(route="/invoice-ocr")
@check_password
def upload_files_page() -> rx.Component:
    return page_template(
        rx.el.div(
            upload_zone(
                loading=VatInvoiceState.up_loading,
                upload_handler=VatInvoiceState.upload_for_vat_invoice(
                    rx.upload_files(upload_id="upload1")  # type:ignore
                ),
            ),
            ag_grid_zone(),
            download_result_button(),
            class_name="flex flex-col items-center justify-center w-full space-y-2",
        )
    )
