import reflex as rx
from reflex.event import EventCallback


def upload_zone(
    loading: bool, upload_handler: EventCallback
) -> rx.Component:
    return rx.upload(
        rx.cond(
            loading,
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
                    "不建议单次上传太多文件，单文件最大5mb",
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
        on_drop=upload_handler,
    )
