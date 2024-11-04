import reflex as rx
from reflex_ag_grid import ag_grid
import os
from ..models import JournalAccount
from .upload import bank_slip_column_defs
from .components.nav_bar import nav_bar
from .components.check_password import check_password
from ..utils.request_api import generate_filename, recognize_filetype
import asyncio

"""
TODO:
1. 加一个发票上传的功能，上传完以后自动将发票文件的链接拷贝到剪贴板，提示用户可以粘贴
2. 


"""
BACK_END = os.getenv("BACK_END")


class DisplayState(rx.State):
    """
    向用户展示数据的 State
    """

    display_data: list[dict] = []  # 展示的数据
    up_loading: bool = False  # 是否有发票文件在上传

    @rx.var
    def data(self) -> list[dict]:
        """
        Ag Grid 组件需要用 computed var 向前端传输数据，用 state var 数据更新会有延迟

        Returns: 展示的数据

        """
        return self.display_data

    def load_data(self) -> None:
        """
        用于在页面加载时从数据库中获取数据
        """
        self.display_data = JournalAccount.get_all_records()

    def cell_value_changed(self, row, col_field, new_value) -> None:
        """
        实时处理用户对表格内容的修改，并更新到数据库
        Args:
            row: 修改单元格的行
            col_field: 修改单元格的列
            new_value: 单元格的更新值
        """
        self.display_data[row][col_field] = new_value  # 获取更新数据
        with rx.session() as session:
            record = session.get(
                JournalAccount, self.display_data[row]["id"]
            )  # 通过id获取更新条目对应的数据库实例
            if record:
                setattr(record, col_field, new_value)  # 修改数据库内的值
                session.commit()

        yield rx.toast(
            f"数据更新, 行: {row}, 列: {col_field}, 更新值: {new_value}",
            duration=2000,
        )  # 向用户发出提示

    async def upload_invoice(self, files: list[rx.UploadFile]):
        """上传发票文件，将发票文件的链接写入用户的剪贴板

        Args:
            files:  reflex 要求上传文件是list，但是上传组件其实只会上传一个文件

        """

        self.up_loading = True

        yield

        await asyncio.sleep(2)

        file = files[0]
        _, file_extension = recognize_filetype(file)  # 检查文件类型 和 文件扩展名
        new_filename = generate_filename(
            file_extension, length=6
        )  # 用时间和随机字符串给文件重新命名
        upload_file = rx.get_upload_dir() / new_filename  # 创建一个保存上传文件的地址
        # 默认保存文件的目录时 upload_files

        upload_data = await file.read()

        with upload_file.open("wb") as file_object:
            file_object.write(upload_data)  # 把文件保存到指定目录

        file_url = f"{BACK_END}/_upload/{new_filename}"

        yield rx.set_clipboard(file_url)

        self.up_loading = False

        yield

        yield rx.toast(
            f"发票文件的链接：{new_filename} 已经拷贝到你的剪贴板，你可以粘贴到对应条目中。",
            close_button=True,
        )


def upload_invoice_button() -> rx.Component:
    return rx.upload(
        rx.cond(
            DisplayState.up_loading,
            rx.flex(
                rx.spinner(size="3", color=rx.color("slate", 2)),
                class_name="w-7 h-7 justify-center items-center",
            ),
            rx.icon("file-up", size=28, color=rx.color("slate", 2)),
        ),
        id="upload_invoice",
        multiple=False,
        accept={
            "application/pdf": [".pdf"],
            "image/png": [".png"],
            "image/bmp": [".bmp"],
            "image/jpeg": [".jpg", ".jpeg"],
        },
        max_size=5000000,  # 百度api最大文件限制 8mb
        no_drag=True,
        disabled=rx.cond(DisplayState.up_loading, True, False),
        on_drop=DisplayState.upload_invoice(
            rx.upload_files(upload_id="upload_invoice")
        ),  # type:ignore
        bg=rx.color("slate", 12),
        class_name="fixed right-20 bottom-20 rounded-full !p-4 !border-0",
    )


def ag_grid_zone() -> rx.Component:
    return ag_grid(
        id="ag_grid_basic_editing",
        row_data=DisplayState.data,
        column_defs=bank_slip_column_defs,
        on_cell_value_changed=DisplayState.cell_value_changed,
        width="90vw",
        height="90vh",
        pagination=True,
    )


@rx.page(route="/display", title="账目一览-EasyFinance", on_load=DisplayState.load_data)
@check_password
def display() -> rx.Component:
    return rx.fragment(
        rx.flex(
            nav_bar(),
            ag_grid_zone(),
            justify="center",
            padding_top="2rem",
            direction="column",
            align="center",
            padding="0",
        ),
        upload_invoice_button(),
    )
