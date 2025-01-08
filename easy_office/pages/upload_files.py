from typing import AsyncGenerator

import reflex as rx

from ..utils.file_process import save_file_list
from .components.check_password import check_password
from .components.template import page_template
from .components.upload_zone import upload_zone


class UploadFileState(rx.State):
    """管理上传文件的 state
    up_loading：目前是否有文件正在上传
    data：上传文件的信息；list[tuple[str, str]] 第一个 str 是原始文件名，第二个 str 是上传后的文件名
    """

    up_loading: bool = False
    data: rx.Field[list[tuple[str, str]]] = rx.field([])

    @rx.event
    async def upload_file(
        self, files: list[rx.UploadFile]
    ) -> AsyncGenerator:
        """上传文件，将文件的链接写入用户的剪贴板

        Args:
            files:  文件list

        """

        self.up_loading = True

        try:
            # 上传文件
            file_list = await save_file_list(files)

            # 原始文件名列表
            origin_file_name_list: list[str] = [
                file.filename.strip("./")
                for file in files
                if file.filename
            ]

            # 新文件名列表
            new_file_name_list: list[str] = [
                file.name for file in file_list
            ]

            self.data.extend(
                list(
                    zip(
                        origin_file_name_list,
                        new_file_name_list,
                    )
                )
            )

            yield
        except Exception as e:
            yield rx.toast.error(f"{e}", close_button=True)

        finally:
            self.up_loading = False

    @rx.event
    def toast_copy_file_url(self, file_url: str):
        yield rx.toast.success(
            message=f"成功复制链接：{file_url}",
            close_button=True,
            duration=5000,
        )


def table_header() -> rx.Component:
    """表头"""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(
                "文件名", width="20vw"
            ),
            rx.table.column_header_cell(
                "文件链接", width="50vw"
            ),
            rx.table.column_header_cell(
                "Action", width="20vw"
            ),
        )
    )


def render_file_data(
    file_data: tuple[str, str],
) -> rx.Component:
    """渲染数据行

    Args:
        file_data (tuple[str, str]): 上传文件的数据，第一个 str 是原始文件名，第二个 str 是上传后的文件名

    """
    file_url = rx.get_upload_url(file_data[1])
    return rx.table.row(
        rx.table.cell(file_data[0]),  # 文件名
        rx.table.cell(file_url),  # 文件链接
        rx.table.cell(  # Action，点击按钮将链接复制到剪贴板
            rx.button(
                "复制链接",
                on_click=[
                    rx.set_clipboard(content=file_url),
                    UploadFileState.toast_copy_file_url(
                        file_url
                    ),
                ],
                color=rx.color("slate", 2),
                bg=rx.color("slate", 12),
            )
        ),
    )


def file_data_table() -> rx.Component:
    return rx.table.root(
        table_header(),
        rx.table.body(
            rx.foreach(
                iterable=UploadFileState.data,
                render_fn=render_file_data,
            ),
        ),
    )


@rx.page(route="/upload-files")
@check_password
def upload_files_page() -> rx.Component:
    return page_template(
        upload_zone(
            loading=UploadFileState.up_loading,
            upload_handler=UploadFileState.upload_file(
                rx.upload_files(upload_id="upload1")  # type:ignore
            ),
        ),
        file_data_table(),
    )
