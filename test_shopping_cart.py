import re
import logging

import allure
import pytest
from allure_commons.types import AttachmentType
from selene import browser, have
from selenium import webdriver
import requests

BASE_URL = 'https://demowebshop.tricentis.com'


@pytest.fixture(scope='session', autouse=True)
def custom_browser():
    options = webdriver.FirefoxOptions()
    options.page_load_strategy = 'eager'
    browser.config.driver_options = options
    browser.config.window_height = '1080'
    browser.config.window_width = '1920'
    browser.config.base_url = BASE_URL


@pytest.fixture(scope='session')
def authorization():
    user_data = {
        'email': 'ssuxxarr@mail.ru',
        'password': '12345678',
        'RememberMe': False
    }
    with allure.step("Авторизация пользователя"):
        response = post_with_logging(BASE_URL + '/login', data=user_data, allow_redirects=False)
        auth_cookie = response.cookies.get('NOPCOMMERCE.AUTH')
        auth_data = (user_data, auth_cookie)

    yield auth_data

    with allure.step("Очитска корзины"):
        response_cart = requests.get(BASE_URL + "/cart", cookies={'NOPCOMMERCE.AUTH': auth_cookie})
        find = re.findall(r'removefromcart" value="(\d+)', response_cart.text)
        for good_id in find:
            response = post_with_logging(BASE_URL + '/cart',
                                         data={
                                             'removefromcart': good_id,
                                             f'itemquantity{good_id}': 0,
                                             'updatecart': 'Update shopping cart'},
                                         cookies={'NOPCOMMERCE.AUTH': auth_cookie})
            assert response.status_code == 200


@allure.title("Добавление товара в пустую корзину авторизованным пользователем")
def test_add_goods_to_empty_cart_by_authorized_user(authorization):
    user_data, auth_cookie = authorization
    with allure.step("Добавление товара в корзину"):
        response = post_with_logging(BASE_URL + "/addproducttocart/catalog/36/1/1",
                                     cookies={'NOPCOMMERCE.AUTH': auth_cookie})
        assert response.status_code == 200

    with allure.step("Отркрытие корзины в браузере с авторизационным cookie"):
        browser.open('/cart')
        browser.driver.add_cookie({'name': 'NOPCOMMERCE.AUTH', 'value': auth_cookie})
        browser.open('/cart')

    with allure.step("Проверка, что пользователь авторизован"):
        browser.element('.header .account').should(have.exact_text(user_data['email']))

    with allure.step("Проверка, что товар добавлен в корзину"):
        browser.element(".product-name").should(have.exact_text('Blue Jeans'))


@allure.title("Добавление товара в корзину, в которой уже есть  товары, авторизованным пользователем")
def test_add_to_non_empty_car_by_authorized_user(authorization):
    user_data, auth_cookie = authorization
    with allure.step("Добавление товара в корзину"):
        response = post_with_logging(BASE_URL + "/addproducttocart/catalog/36/1/1",
                                     cookies={'NOPCOMMERCE.AUTH': auth_cookie})
    assert response.status_code == 200

    with allure.step("Отркрытие корзины в браузере с авторизационным cookie"):
        browser.open('/cart')
        browser.driver.add_cookie({'name': 'NOPCOMMERCE.AUTH', 'value': auth_cookie})
        browser.open('/cart')

    with allure.step("Проверка, что пользователь авторизован"):
        browser.element('.header .account').should(have.exact_text(user_data['email']))

    with allure.step("Проверка, что в корзине есть товар"):
        browser.element(".product-name").should(have.exact_text('Blue Jeans'))

    with allure.step("Добавление товаров в корзину"):
        response = post_with_logging(BASE_URL + "/addproducttocart/catalog/31/1/1",
                                     cookies={'NOPCOMMERCE.AUTH': auth_cookie})
        assert response.status_code == 200
        response = post_with_logging(BASE_URL + "/addproducttocart/catalog/40/1/1",
                                     cookies={'NOPCOMMERCE.AUTH': auth_cookie})
        assert response.status_code == 200

    with allure.step("Проверка что новые товары добавлены в корзину"):
        browser.open('/cart')
        browser.all(".product-name").should(have.exact_texts('Blue Jeans', '14.1-inch Laptop',
                                                             'Casual Golf Belt'))


def post_with_logging(url, **kwars):
    with allure.step("Logging API"):
        response = requests.post(url, **kwars)
        allure.attach(body=response.text, name="Response",
                      attachment_type=AttachmentType.TEXT, extension=".txt")
        allure.attach(body=str(response.cookies), name="Cookies", attachment_type=AttachmentType.TEXT, extension=".txt")
        logging.info(f'POST: {response.request.url}')
        logging.info(f'With payload {response.request.body}')
        logging.info(f'Finished with status code {response.status_code}')
        return response
