import asyncpg
from aiogram import Router, F
from aiogram.types import Message
import os
import requests
import folium
from folium.plugins import MarkerCluster
from app.URL import OPENROUTESERVICE_API_KEY, FOURSQUARE_API_KEY
from database.module import DATABASE_URL
from app.handlers import router


@router.message(F.text == "Построить маршрут с предпочтениями")
async def build_route_with_preferences(message: Message):
    user_id = message.from_user.id

    # Подключаемся к базе данных
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT latitude, longitude, preferences FROM users WHERE user_id = $1", user_id)
    await conn.close()

    # Проверяем, есть ли у пользователя сохраненная геолокация и предпочтения
    if not user or user['latitude'] is None or user['longitude'] is None:
        await message.answer("Пожалуйста, сначала отправьте вашу геолокацию.")
        return
    if not user['preferences']:
        await message.answer("Пожалуйста, сначала укажите ваши предпочтения.")
        return

    # Координаты пользователя
    user_latitude = user['latitude']
    user_longitude = user['longitude']
    user_location = [user_latitude, user_longitude]

    # Получаем предпочтения пользователя
    preferences = user['preferences'].split(",")  # Предположим, что предпочтения хранятся в виде строки, разделенной запятыми

    # Запрос к Foursquare API для получения мест с учетом предпочтений
    try:
        places = await get_places_with_preferences(user_location, preferences)

        if not places:
            await message.answer("Не удалось найти места, соответствующие вашим предпочтениям.")
            return

        # Сортируем места по рейтингу (от высокого к низкому)
        places_sorted = sorted(places, key=lambda x: x["rating"], reverse=True)

        # Выбираем топ-5 мест
        top_places = places_sorted[:5]

        # Формируем координаты для маршрута
        route_coordinates = [user_location] + [[place["latitude"], place["longitude"]] for place in top_places]

        # Построение маршрута с помощью OpenRouteService API
        route_data = build_route(route_coordinates, OPENROUTESERVICE_API_KEY)

        # Создаем карту с маршрутом и местами
        map_file = create_map(user_location, top_places, route_data)

        # Отправляем карту пользователю
        with open(map_file, "rb") as file:
            await message.answer_document(file)

        # Удаляем файл карты после отправки
        os.remove(map_file)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")


# Функция для получения мест с учетом предпочтений
async def get_places_with_preferences(location, preferences, radius=5000, limit=10):
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {
        "ll": f"{location[0]},{location[1]}",  # Координаты пользователя
        "radius": radius,  # Радиус поиска в метрах
        "limit": limit,  # Количество мест
        "query": ",".join(preferences)  # Ключевые слова для поиска
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Проверяем статус ответа
        data = response.json()

        # Извлекаем места с рейтингом
        places = []
        for place in data.get("results", []):
            name = place.get("name")
            location = place.get("geocodes", {}).get("main", {})
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            rating = place.get("rating", 0)  # Рейтинг (если доступен)
            if latitude and longitude:
                places.append({
                    "name": name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "rating": rating
                })
        return places
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка при запросе к Foursquare API: {e}")


# Функция для построения маршрута (OpenRouteService API)
def build_route(coordinates, api_key):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "coordinates": coordinates
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Проверяем статус ответа
    return response.json()


# Функция для создания карты
def create_map(center_location, top_places, route_data):
    m = folium.Map(location=center_location, zoom_start=13)

    # Добавляем маршрут на карту
    if "features" in route_data:
        folium.PolyLine(
            locations=[
                [coord[1], coord[0]] for coord in route_data["features"][0]["geometry"]["coordinates"]
            ],
            color="blue",
            weight=5,
            opacity=0.7
        ).add_to(m)

    # Добавляем маркеры для мест
    marker_cluster = MarkerCluster().add_to(m)
    for place in top_places:
        folium.Marker(
            location=[place["latitude"], place["longitude"]],
            popup=f"{place['name']} (Рейтинг: {place['rating']})",
            icon=folium.Icon(color="green", icon="info-sign")
        ).add_to(marker_cluster)

    # Сохраняем карту в HTML-файл
    map_file = "recommended_places_route.html"
    m.save(map_file)
    return map_file
