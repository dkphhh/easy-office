import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator

import reflex as rx
from reflex_ag_grid import ag_grid

from ..utils.file_process import (
    generate_filename,
    save_file_list,
)
from ..utils.request_api import (
    Request_Baidu_OCR,
    create_new_record,
)

BACK_END = os.getenv("BACK_END")


class UploadState(rx.State):
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
    async def upload_for_ocr(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator:
        """
        调用百度云的api，上传用户传入的文件，将返回的数据赋值给 self.upload_data
        Args:
            files: 用户上传的文件

        """
        self.up_loading = True  # 显示加载状态

        yield

        if len(files) > 5:
            yield rx.toast.error(
                f"一次最多传5个文件，你传了{len(files)}个"
            )
            raise AttributeError(
                f"一次最多传5个文件，你传了{len(files)}个"
            )

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

            raise e

        finally:
            self.up_loading = False

    @rx.event
    async def upload_file(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator:
        """上传文件，将文件的链接写入用户的剪贴板

        Args:
            files:  reflex 要求上传文件是list，但是上传组件其实只会上传一个文件

        """

        self.up_loading = True

        yield

        file = files[0]
        file_extension = "." + file.filename.split(".")[-1]  # type:ignore
        new_filename = generate_filename(
            file_extension, length=6
        )  # 用时间和随机字符串给文件重新命名
        upload_file = (
            rx.get_upload_dir() / new_filename
        )  # 创建一个保存上传文件的地址
        # 默认保存文件的目录时 upload_files

        upload_data = await file.read()

        with upload_file.open("wb") as file_object:
            file_object.write(
                upload_data
            )  # 把文件保存到指定目录

        file_url = f"{BACK_END}/_upload/{new_filename}"
        # 将文件链接写入剪贴板
        yield rx.set_clipboard(file_url)

        self.up_loading = False

        yield rx.toast(
            f"文件的链接：{file_url} 已经拷贝到你的剪贴板，你可以粘贴到对应条目中。",
            close_button=True,
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
    ag_grid.column_def(
        field="tax_invoice_url",
        header_name="发票",
        cell_data_type="text",
        editable=True,
        filter=None,
        cell_editor=ag_grid.editors.text,
        sortable=False,  # type:ignore
    ),
]


def ag_grid_zone() -> rx.Component:
    return rx.vstack(
        ag_grid(
            id="ag_grid_basic_editing",
            row_data=UploadState.data,
            column_defs=bank_slip_column_defs,
            on_cell_value_changed=UploadState.cell_value_changed,
            width="90vw",
            height="60vh",
        ),
    )


def upload_zone() -> rx.Component:
    return rx.upload(
        rx.cond(
            UploadState.up_loading,
            rx.hstack(
                rx.spinner(size="3"),
                align="center",
                justify="center",
                height="100%",
            ),
            rx.vstack(
                rx.text(
                    "点击方框，或将文件拖入框内", size="1"
                ),
                rx.text(
                    "支持 .jpg .jpeg .png .bmp .pdf 文件",
                    size="1",
                ),
                rx.text(
                    "最多同时上传5个文件，单文件最大5mb",
                    size="1",
                ),
                spacing="1",
                height="100%",
                justify="center",
                align="center",
            ),
        ),
        id="upload1",
        multiple=True,
        # max_files=5, # Reflex 给的这个参数似乎不能限制前端上传的文件数量，所以我采用了后端验证的方式
        max_size=5000000,  # 百度api最大文件限制 8mb
        border="1px dotted",
        class_name="rounded-md",
        width="90vw",
        height="150px",
        padding="0px",
        accept={
            "image/png": [".png"],
            "image/jpeg": [".jpg", ".jpeg"],
            "image/bmp": [".bmp"],
            "application/pdf": [".pdf"],
        },
        on_drop=UploadState.upload_for_ocr(
            rx.upload_files(upload_id="upload1")  # type:ignore
        ),  # type:ignore
    )


def send_records_button() -> rx.Component:
    return rx.button(
        "发送数据",
        on_click=UploadState.send_to_database,
        color=rx.color("slate", 2),
        bg=rx.color("slate", 12),
        loading=UploadState.up_loading,
    )


def upload_file_button() -> rx.Component:
    return rx.upload(
        rx.vstack(
            rx.cond(
                UploadState.up_loading,
                rx.flex(
                    rx.spinner(
                        size="3", color=rx.color("slate", 2)
                    ),
                    class_name="w-6 h-6 justify-center items-center",
                ),
                rx.tooltip(
                    rx.icon(
                        "file-up",
                        size=24,
                        color=rx.color("slate", 2),
                    ),
                    content="将其他文件上传到服务器",
                ),
            ),
            justify="center",
            align="center",
            spacing="1",
        ),
        id="upload_file",
        multiple=False,
        accept={
            "application/pdf": [".pdf"],
            "image/png": [".png"],
            "image/bmp": [".bmp"],
            "image/jpeg": [".jpg", ".jpeg"],
        },
        max_size=5000000,  # 限制文件大小
        no_drag=True,
        disabled=rx.cond(
            UploadState.up_loading, True, False
        ),
        on_drop=UploadState.upload_file(
            rx.upload_files(upload_id="upload_file")  # type:ignore
        ),
        bg=rx.color("slate", 12),
        class_name="fixed right-10 bottom-10 rounded-full !p-2  !border-0",
    )


def upload_and_send() -> rx.Component:
    return rx.vstack(
        upload_zone(),
        ag_grid_zone(),
        send_records_button(),
        upload_file_button(),
        class_name="",
        width="100%",
        align="center",
        justify="center",
    )
