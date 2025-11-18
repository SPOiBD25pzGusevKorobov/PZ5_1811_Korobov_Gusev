import sys
import requests
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
)

BASE = "https://world.openfoodfacts.org"
HEADERS = {
    "User-Agent": "PyQt-CalorieFetcher/1.0 (+https://example.com)"
}

def get_product_by_barcode(barcode: str, fields=None, lang="ru", country="ru") -> dict:
    if fields is None:
        fields = "code,product_name,nutriments,brands,quantity,serving_size,language,lang,lc"
    url = f"{BASE}/api/v2/product/{barcode}"
    params = {"fields": fields, "lc": lang, "cc": country}
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def search_products(query: str, page_size=10, fields=None, lang="ru", country="ru") -> dict:
    if fields is None:
        fields = "code,product_name,brands,nutriments,quantity,serving_size,ecoscore_grade,categories,categories_tags"
    url = f"{BASE}/api/v2/search"
    params = {
        "search_terms": query,
        "fields": fields,
        "page_size": page_size,
        "lc": lang,
        "cc": country,
    }
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def extract_kcal(nutriments: dict) -> dict:
    get = nutriments.get
    data = {
        "kcal_100g": get("energy-kcal_100g") or get("energy-kcal_value"),
        "protein_100g": get("proteins_100g"),
        "fat_100g": get("fat_100g"),
        "carbs_100g": get("carbohydrates_100g"),
        "kcal_serving": get("energy-kcal_serving"),
        "protein_serving": get("proteins_serving"),
        "fat_serving": get("fat_serving"),
        "carbs_serving": get("carbohydrates_serving"),
    }
    return {k: v for k, v in data.items() if v is not None}

class CalorieSearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Поиск калорийности продуктов")
        self.resize(600, 500)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Barcode Section
        barcode_layout = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Введите штрихкод")
        barcode_layout.addWidget(self.barcode_input)
        self.barcode_btn = QPushButton("Поиск по штрихкоду")
        self.barcode_btn.clicked.connect(self.search_barcode)
        barcode_layout.addWidget(self.barcode_btn)
        self.layout.addLayout(barcode_layout)

        # Name Section
        name_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите название")
        name_layout.addWidget(self.name_input)
        self.name_btn = QPushButton("Поиск по названию или категории")
        self.name_btn.clicked.connect(self.search_name)
        name_layout.addWidget(self.name_btn)
        self.layout.addLayout(name_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.layout.addWidget(self.result_text)

    def search_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            self.result_text.setText("Введите штрихкод!")
            return
        try:
            prod = get_product_by_barcode(barcode)
            if prod.get("product"):
                p = prod["product"]
                msg = (
                    f"Название: {p.get('product_name')}\n"
                    f"Бренд: {p.get('brands')}\n"
                    f"Упаковка: {p.get('quantity')}\n"
                    f"Порция: {p.get('serving_size')}\n"
                    f"Категории: {p.get('categories') if p.get('categories') else '-'}\n"
                    f"Нутриенты: {extract_kcal(p.get('nutriments', {}))}\n"
                )
            else:
                msg = "Продукт не найден"
            self.result_text.setText(msg)
        except Exception as e:
            self.result_text.setText(f"Ошибка запроса: {str(e)}")

    def search_name(self):
        name = self.name_input.text().strip().lower()
        if not name:
            self.result_text.setText("Введите название")
            return
        try:
            res = search_products(name, page_size=20)
            products = res.get("products", [])
            msgs = []
            num = 1
            for p in products:
                title = (p.get('product_name') or "").lower()
                categories = (p.get('categories') or "").lower()
                categories_tags = [tag.lower() for tag in (p.get('categories_tags') or [])]
                nutr = extract_kcal(p.get('nutriments', {}))
                # фильтр: ищет по названию, по строке категории, или по элементу в categories_tags
                if nutr and (
                        (title and name in title)
                        or (categories and name in categories)
                        or any(name in tag for tag in categories_tags)
                ):
                    info = (
                        f"Результат {num}:\n"
                        f"Штрихкод: {p.get('code')}\n"
                        f"Название: {p.get('product_name')}\n"
                        f"Категории: {categories}\n"
                        f"Категории-теги: {', '.join(categories_tags)}\n"
                        f"Бренд: {p.get('brands') if p.get('brands') else '-'}\n"
                        f"Нутриенты: {nutr}\n"
                    )
                    msgs.append(info)
                    num += 1
            self.result_text.setText(
                '\n'.join(msgs) if msgs else "Нет продуктов с подходящим названием или категорией.")
        except Exception as e:
            self.result_text.setText(f"Ошибка запроса: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalorieSearchWindow()
    window.show()
    sys.exit(app.exec())