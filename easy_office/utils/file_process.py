import random
import string
from datetime import datetime
from io import BytesIO
from pathlib import Path

import reflex as rx
from pypdf import PdfReader, PdfWriter


def generate_random_string(length: int = 12) -> str:
    """生成指定长度的随机字符串"""
    # 定义字符池
    characters = (
        string.ascii_letters + string.digits
    )  # 包含大小写字母和数字
    return "".join(
        random.choice(characters) for _ in range(length)
    )


def generate_filename(file_extension: str, length=6) -> str:
    """生成随机字符串,格式：时间+6位随机字符
    Args:
        file_extension：文件扩展名，例如：.pdf
        length: 字符串长度
    """
    characters = string.ascii_letters + string.digits
    random_string = "".join(
        random.choice(characters) for _ in range(length)
    )
    new_file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{random_string}{file_extension}"
    return new_file_name


async def save_file(file: rx.UploadFile) -> Path:
    file_name = file.filename.lower()  # type: ignore
    ext = "." + file_name.split(".")[-1]
    new_filename = generate_filename(
        ext, length=6
    )  # 用时间和随机字符串给文件重新命名
    upload_file: Path = (
        rx.get_upload_dir() / new_filename
    )  # 创建一个保存上传文件的地址,默认保存文件的目录是 upload_files
    upload_data: bytes = await file.read()

    with upload_file.open("wb") as file_object:
        file_object.write(
            upload_data
        )  # 把文件保存到指定目录

    return upload_file


async def process_pdf_file(
    pdf_file: rx.UploadFile,
) -> list[Path]:
    """处理PDF文件，如果是多页则分割成单页"""
    pdf_file.file.seek(0)  # 确保从文件开始读取
    reader = PdfReader(pdf_file.file)

    # 单页PDF直接保存
    if len(reader.pages) <= 1:
        pdf_file.file.seek(0)  # 重置文件指针
        saved_file = await save_file(pdf_file)
        return [saved_file]

    # 多页PDF进行分割
    saved_files: list[Path] = []
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        with BytesIO() as bytes_stream:
            writer.write(bytes_stream)
            bytes_stream.seek(0)

            split_pdf = rx.UploadFile(
                file=bytes_stream,
                filename=f"{pdf_file.filename.rsplit('.', 1)[0]}-page{i+1}.pdf",  # type:ignore
            )
            saved_file = await save_file(split_pdf)
            saved_files.append(saved_file)

    return saved_files


async def save_file_list(
    files: list[rx.UploadFile],
) -> list[Path]:
    files_list: list[Path] = []

    for file in files:
        file_name = file.filename.lower()  # type: ignore
        file_suffix = "." + file_name.split(".")[-1]

        if file_suffix == ".pdf":
            pdf_list = await process_pdf_file(file)

            files_list.extend(pdf_list)

        else:
            files_list.append(await save_file(file))

    return files_list
