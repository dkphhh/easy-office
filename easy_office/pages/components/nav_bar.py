import reflex as rx
from reflex.style import color_mode, toggle_color_mode


def dark_mode_toggle() -> rx.Component:
    """全局切换亮/暗模式"""
    return rx.flex(
        rx.button(
            rx.cond(
                color_mode == "light",
                rx.icon(
                    "sun",
                    size=25,
                    color=rx.color("slate", 12),
                ),
                rx.icon(
                    "moon",
                    size=25,
                    color=rx.color("slate", 12),
                ),
            ),
            on_click=toggle_color_mode,
            padding=0,
            variant="ghost",
            width="40px",
            height="40px",
        ),
        width="160px",
        justify="end",
    )


class NavItem(rx.Base):
    name: str = ""
    path: str = ""


class NavBarState(rx.State):
    items: list[NavItem] = [
        NavItem(name="快捷记账", path="/"),
        NavItem(name="文件上传", path="/upload-files"),
        NavItem(name="发票识别", path="/invoice-ocr"),
        NavItem(
            name="账目一览",
            path="https://yuanwang.feishu.cn/base/MFoQbIqCNaujgzsn7vOcTfpBnjb?table=tblrtFGd80L0Z0Hk&view=vewfVnLasa",
        ),
    ]


def render_nav_item(item: NavItem) -> rx.Component:
    return rx.el.h2(
        rx.link(
            item.name,
            href=item.path,
            color=rx.cond(
                rx.State.router.page.path == item.path,
                rx.color("slate", 12),
                rx.color("slate", 10),
            ),
        ),
        class_name="font-bold text-xl",
    )


def nav_bar() -> rx.Component:
    return rx.el.nav(
        rx.el.div(
            rx.el.div(
                rx.el.h1(
                    rx.link(
                        "EasyOffice",
                        href="/",
                        color=rx.color("slate", 2),
                    ),
                    class_name="text-2xl font-bold",
                ),
                bg=rx.color("slate", 12),
                class_name="flex rounded-full py-1 px-4 w-40 justify-center items-center",
            ),
            rx.el.div(
                rx.foreach(
                    NavBarState.items, render_nav_item
                ),
                class_name="flex flex-row justify-center items-center space-x-5",
            ),
            dark_mode_toggle(),
            class_name="flex flex-row justify-between items-center w-4/5 h-12",
        ),
        bg=rx.color("slate", 2),
        class_name="flex flex-row justify-center items-center w-10/12 h-16 m-2 rounded-full",
    )
