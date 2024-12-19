import os
from typing import Any, Callable

import reflex as rx

PASSWORD = os.getenv("PASSWORD")


class PassState(rx.State):
    """进入网站后的密码验证"""

    session_token: str = rx.LocalStorage(
        name="session_token", sync=True
    )

    @rx.var
    def check(self) -> bool:
        if self.session_token:
            return (
                True
                if self.session_token == PASSWORD
                else False
            )

        return False

    @rx.event
    def check_input(
        self, value: dict[str, Any]
    ) -> None | rx.Component:
        """用于验证用户输入的值是否等于环境变量里的 PASSWORD

        Args:
            value (dict[str, str]): 前端提交的表单值

        Returns:
            None | rx.Component: 如果密码正确不返回值，如果密码错误,在前端显示一个小提示
        """
        if value["password"] == PASSWORD:
            self.session_token = PASSWORD  # type:ignore
        else:
            return rx.toast.warning(
                "密码错误!",
                close_button=True,
                duration=3000,
            )


def check_password(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        return rx.fragment(
            rx.cond(  # type:ignore
                PassState.check,
                func(*args, **kwargs),
                rx.form(  # 输入密码的表单
                    rx.vstack(
                        rx.vstack(
                            rx.text(
                                "仅限内部人士使用", size="3"
                            ),
                            rx.text(
                                "Only for insiders",
                                size="1",
                            ),
                            spacing="1",
                            justify="center",
                            align="center",
                        ),
                        rx.hstack(
                            rx.input(
                                name="password",
                                placeholder="请输入密码",
                                type="password",
                                required=True,
                            ),
                            rx.button(
                                "确定",
                                type="submit",
                                color=rx.color("slate", 2),
                                bg=rx.color("slate", 12),
                            ),
                            spacing="1",
                            justify="center",
                            align="center",
                        ),
                        spacing="2",
                        height="100vh",
                        width="100vw",
                        justify="center",
                        align="center",
                    ),
                    on_submit=PassState.check_input,
                ),
            ),
        )

    return wrapper
