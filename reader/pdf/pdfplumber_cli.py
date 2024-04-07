import pdfplumber
from PIL import ImageDraw, ImageFont


def read_pdf():
    with pdfplumber.open("The-Modern-Olympic-Games.pdf") as pdf:
        for page_number in range(len(pdf.pages)):
            page = pdf.pages[page_number]
            page_image = page.to_image(resolution=320)

            # 遍历页面中的每个图片对象
            for image_idx, image_obj in enumerate(page.images):
                x0, y0, x1, y1 = (
                    image_obj["x0"],
                    image_obj["y0"],
                    image_obj["x1"],
                    image_obj["y1"],
                )
                image = page_image.original
                draw = ImageDraw.Draw(image)
                image_width, image_height = page_image.original.size
                ratio = image_height / page.height
                draw.rectangle(
                    (
                        (x0 * ratio, y0 * ratio),
                        (x1 * ratio, y1 * ratio),
                    ),
                    outline="red",
                    width=6,
                )
                draw.text(
                    (x0 * ratio, y0 * ratio),
                    "image",
                    fill="blue",
                    font=ImageFont.load_default(100),
                )

            if len(page.images) != 0:
                # 保存图片到本地文件
                image_path = f"page_{page_number}.png"
                image.save(image_path)
                print(f"Saved image: {image_path}")
