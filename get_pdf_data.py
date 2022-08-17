import fitz
import json
from pdfquery import pdfquery
from bs4 import BeautifulSoup
from PIL import Image
from pyzbar import pyzbar

# Функция, формирующая словарь с Текстом и координаты)
def pdf_get_text(file):

    # Получаем Высоту страниц, это необходимо по следующей причине: в pdfquery y0 считается от нижней части страницы,
    # а в pyzbar, через который мы будем получать координаты штрих-кодов, y0 считается от верхней части страницы,
    # поэтому координаты pdfquery по оси y нужно "перевернуть"
    with fitz.open(file) as doc:
        all_text = {}

        for num, page in enumerate(doc.pages()):
            all_text[num] = json.loads(page.get_text('json'))
            height_page = all_text[num]['height']
            break

    # Объявляем экземпляр класса
    pdf = pdfquery.PDFQuery(file)
    pdf.load()
    #  (!) Забираем сразу весь текст файла без разделения по страницам, но можно сделать и с разделением через
    #  добавление атрибута к pq (такого условия не было, поэтому в результирущем словаре собирается весь текст по
    #  порядку без указания номеров страниц)
    pdf_pages = pdf.pq
    # Будем парсить через BeautifulSoup для поиска каждого элемента по тэгу lttextlinehorizontal (это позволит
    # сохранить структуру документа)
    soup = BeautifulSoup(str(pdf_pages), 'lxml')
    # Собираем промежуточный словарь (без штрих-кодов) и без учета, что одна сущность может быть разбита на несколько
    # строк (например, NOTES в дополнительно pdf-файле для тестирования скрипта)
    temp_dict = {}
    array_for_check = []
    counter = 0
    # За один цикл соберем список с Текстами и Словарь с Текстами и координатами (можно было обойтись и без списка, но
    # с ним удобнее собирать словарь, т.к. иногда нужно работать сразу с двумя элементами: текущим и предшествующим)
    for item in soup.find_all("lttextboxhorizontal"):
        array_for_check.append(str(item.text))
        # Если Текст есть в списке, но его нет в словаре, то просто добавляем данные
        # + дополнительные вычисления нужны потому, что у pdfquery по дэфолту отсчет по y ведется от нижней части
        # страницы (0), поэтому "переворачиваю" шкалу, т.к. точкой отсчета координат штрих-кодов по оси y будет верх
        bbox = {}
        bbox['x0'] = float(item['x0'])
        bbox['y0'] = round(height_page - float(item['y1']), 3)
        bbox['x1'] = float(item['x1'])
        bbox['y1'] = round(height_page - float(item['y0']), 3)
        temp_dict[counter] = [str(item.text), bbox]
        counter += 1

    # Объединяем единые айтемы, расположенные на разных строках (исключение – первый айтем, т.к. может быть заголовком),
    # например, в NOTES может быть не одна строка, а несколько. Полученный словарь уже будет использоваться функцией,
    # которая будет объединять словарь с Текстом и словарь со Штрих-кодами
    temp = []
    text_dict = {}
    for i in range(len(array_for_check)):
        # Если в найденном тексте нет ":" (и это не первый элемент), значит, это часть текста, расположенного выше
        if ':' not in array_for_check[i] and i != 0:
            # Если список temp не является пустым, т.е. ранее был Текст без ':', и сейчас нам вновь встретился текст без
            # ":", то нужно актуализировать temp (соединить текст и обновить координаты)
            if temp:
                # Актуализируем координаты для "слепленной сущности"
                # для x0
                x0_1 = temp[1]['x0']
                x0_2 = temp_dict[i][1]['x0']
                if float(x0_1) < float(x0_2):
                    x0_result = x0_1
                else:
                    x0_result = x0_2
                # для y0
                y0_1 = temp[1]['y0']
                y0_2 = temp_dict[i][1]['y0']
                if float(y0_1) < float(y0_2):
                    y0_result = y0_1
                else:
                    y0_result = y0_2
                # для x1
                x1_1 = temp[1]['x1']
                x1_2 = temp_dict[i][1]['x1']
                if float(x1_1) > float(x1_2):
                    x1_result = x1_1
                else:
                    x1_result = x1_2
                # для y1
                y1_1 = temp[1]['y1']
                y1_2 = temp_dict[i][1]['y1']
                if float(y1_1) > float(y1_2):
                    y1_result = y1_1
                else:
                    y1_result = y1_2

                # Слепляем Текст без ":" с вышестоящим Текстом
                # Добавляем словарь обновленный текст с обновленными координатами
                bbox = {}
                bbox['x0'] = x0_result
                bbox['y0'] = y0_result
                bbox['x1'] = x1_result
                bbox['y1'] = y1_result

                temp = [f'{str(temp[0]).strip()} {str(array_for_check[i]).strip()}', bbox]

                if i != len(array_for_check)-1:
                    continue
                else:
                    text_dict[temp[0]] = temp[1]

            # Если массив temp является пустым, значит ранее был текст с ":", тогда нынешний Текст соединяем с
            # предыдущим, а не с temp
            else:
            # Актуализируем координаты для "слепленной" сущности
            
                # для x0
                x0_1 = temp_dict[i-1][1]['x0']
                x0_2 = temp_dict[i][1]['x0']
                if float(x0_1) < float(x0_2):
                    x0_result = x0_1
                else:
                    x0_result = x0_2
                # для y0
                y0_1 = temp_dict[i-1][1]['y0']
                y0_2 = temp_dict[i][1]['y0']
                if float(y0_1) < float(y0_2):
                    y0_result = y0_1
                else:
                    y0_result = y0_2
                # для x1
                x1_1 = temp_dict[i-1][1]['x1']
                x1_2 = temp_dict[i][1]['x1']
                if float(x1_1) > float(x1_2):
                    x1_result = x1_1
                else:
                    x1_result = x1_2
                # для y1
                y1_1 = temp_dict[i-1][1]['y1']
                y1_2 = temp_dict[i][1]['y1']
                if float(y1_1) > float(y1_2):
                    y1_result = y1_1
                else:
                    y1_result = y1_2

                # Слепляем Текст без ":" с вышестоящим Текстом
                # Добавляем словарь обновленный текст с обновленными координатами
                bbox = {}
                bbox['x0'] = x0_result
                bbox['y0'] = y0_result
                bbox['x1'] = x1_result
                bbox['y1'] = y1_result

                temp = [f'{str(array_for_check[i-1]).strip()} {str(array_for_check[i]).strip()}', bbox]

                if i != len(array_for_check)-1:
                    continue
                else:
                    text_dict[temp[0]] = temp[1]

        # Если Текст содержит ":" или это первый элемент
        else:
            # Если массив temp не пуст, то нужно: 1. добавть его содержимое в словарь, 2. добавить в словарь текущий
            # элемент
            if temp:
                # Добавялем ранее собранную пару ключ-значение
                text_dict[temp[0]] = temp[1]
                temp = []
                # Добавляем новую пару ключ-значение
                text_dict[array_for_check[i]] = temp_dict[i][1]
            # Если массив temp пуст, то просто добавляем текущий элемент
            else:
                # Добавляем новую пару ключ-значение
                text_dict[array_for_check[i]] = temp_dict[i][1]
    return text_dict

# Функция, конвертирущая pdf в png, для дальнейшего поиска штрих-кодов
def pdf_to_png(pdf_file):
    doc = fitz.open(pdf_file)
    for page in doc:
        pix = page.get_pixmap()
        pix.save(f"img/page-{page.number}.png")
        return f'img/page-{page.number}.png'

# Функция, формирующая словарь со Штрих-кодами (+ координаты)
def pdf_get_barcodes(file):
    barcodes_dict = {}
    img = Image.open(file)
    output = pyzbar.decode(img)
    for barcode in output:
        for item in barcode:
            if 'b' in str(item):
                name = str(item).replace('b', '').replace("'", "")
            if 'Point' in str(item):
                bbox = list(item)
                # Забираем только начальные координаты (x0, y0) для соотнесения с ближайшим текстом
                barcodes_dict[name] = bbox[0]

    return barcodes_dict

# Функция для подсчета расстояния между точками (будем использовать для соотнесения штрих-кода с ближайшим текстом)
def distance_between_points(x0_point_1, y0_point_1, x0_point_2, y0_point_2):
    return ((x0_point_2-x0_point_1)**2 + (y0_point_2-y0_point_1)**2)**1/2

# Финализирующая функция: собираем все собранные данные в один словарь
def collect_pdf_data(text_dict, barcodes_dict):

    result_dict = {}

    # Создаем словарь, где будут все расстояния от всех текстовых элементов до штрих-кодов
    distance_dict = {}
    for barcode_text, barcode_bbox in barcodes_dict.items():
        min = 100000
        temp = []
        for text, bbox in text_dict.items():
            distance = distance_between_points(bbox['x0'], bbox['y0'], barcode_bbox[0], barcode_bbox[1])
            if distance < min:
                temp = [text, distance]
                min = distance
                distance_dict[barcode_text] = temp

    # Собираем результирующий словарь + будем использовать список для доп. проверки, чтобы избегать дублирования
    checking_array = []
    for text in text_dict.keys():

        # Проверяем, что у нас на сранице есть штрих-коды для вычисления расстояний
        if distance_dict:
            for barcode_text, array in distance_dict.items():
                # Если Текст – ближайший к штрих-коду, то объединяем их и добавляем в словарь
                if text in array and text not in checking_array:
                    new_text = str(text).replace(':', '').strip()
                    result_dict[new_text] = str(barcode_text).strip()
                    checking_array.append(text)
                    continue
                # Если в Тексте содержатся оба айтема с ":", то сплитуем и добавляем их в словарь
                if ':' in text and text not in checking_array:
                    new_array = str(text).split(':')
                    result_dict[str(new_array[0]).strip()] = str(new_array[1]).strip()
                    checking_array.append(text)
        # Если штрих-кодов нет, то сразу добавляем текст в результирующий словарь
        else:
            # Если в Тексте содержатся оба айтема с ":", то сплитуем и добавляем их в словарь
            if ':' in text and text not in checking_array:
                new_array = str(text).split(':')
                result_dict[str(new_array[0]).strip()] = str(new_array[1]).strip()
                checking_array.append(text)

    return result_dict

def main(filename):

    try:
        # Получаем текст с координатами из файла
        text_dict = pdf_get_text(filename)

        # Получаем текст штрих-кодов с кооринатами
        barcodes_dict = pdf_get_barcodes(pdf_to_png(filename))

        # Объединяем два ранее полученных словаря и выводим результат
        print(f'{filename}: {collect_pdf_data(text_dict, barcodes_dict)}')

    except Exception as ex:
        print(ex)


if __name__ == '__main__':

    main('pdf_files/test_task.pdf')

    # Доп. проверка: в Notes несколько строк текста, но мы должны отнести их в качестве значения к ключу Notes
    main('pdf_files/multiline_test.pdf')
