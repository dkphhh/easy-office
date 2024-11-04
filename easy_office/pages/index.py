import os

import reflex as rx
from .components.check_password import check_password
from .components.nav_bar import nav_bar
from .upload import upload_and_send

meta = [{"name": "keywords", "content": "发票,银行回单,图片,PDF,识别,转Excel"}]


@rx.page(
    route="/",
    title="快捷记账-EasyOffice",
    description="自动识别银行回单，并导入到数据库",
    meta=meta,
)
@check_password
def index() -> rx.Component:
    """主页面"""
    return rx.vstack(
        nav_bar(),
        upload_and_send(),  # 上传银行回单、识别、将结果上传到数据库
        width="100vw",
        spacing="1",
        align="center",
    )
