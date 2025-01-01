import reflex as rx
from .nav_bar import nav_bar

def page_template(*children) -> rx.Component:
    """主页面"""
    return rx.vstack(
        nav_bar(),
        *children,
        width="100vw",
        spacing="1",
        align="center",
    )