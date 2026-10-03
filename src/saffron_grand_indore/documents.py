from langchain_core.documents import Document


def json_to_markdown(data, source_name="saffron_grand_structured_data.json"):
    docs = []

    for room in data["rooms"]:
        content = (
            f"Room Type: {room['room_type']}\n"
            f"Price per night: ₹{room['price_inr_per_night']}\n"
            f"Capacity: {room['capacity']} guests\n"
            f"Amenities: {', '.join(room['amenities'])}"
        )
        docs.append(Document(page_content=content, metadata={
            "doc_type": "room", "name": room["room_type"], "source": source_name,
        }))

    for restaurant in data["restaurants"]:
        content = (
            f"Restaurant: {restaurant['name']}\n"
            f"Cuisine: {restaurant['cuisine']}\n"
            f"Role: {restaurant['role']}\n"
            f"Hours: {restaurant['hours']}\n"
            f"Online Ordering: {restaurant['orderable_online']}"
        )
        docs.append(Document(page_content=content, metadata={
            "doc_type": "restaurant", "name": restaurant["name"], "source": source_name,
        }))

    for item in data["menu"]:
        content = (
            f"Item: {item['item']}\n"
            f"Category: {item['category']}\n"
            f"Price: ₹{item['price_inr']}\n"
            f"Vegetarian: {item['veg']}\n"
            f"Spice Level: {item['spice_level']}\n"
            f"Description: {item['description']}"
        )
        docs.append(Document(page_content=content, metadata={
            "doc_type": "menu_item", "name": item["item"], "category": item["category"], "source": source_name,
        }))

    room_service = data["room_service"]
    content = (
        f"Room Service Available: {room_service['available']}\n"
        f"Hours: {room_service['hours']}\n"
        f"Menu Source: {room_service['menu_source']}\n"
        f"Delivery Charge: ₹{room_service['delivery_charge_inr']}\n"
        f"Average Delivery Time: {room_service['average_delivery_time_minutes']} minutes"
    )
    docs.append(Document(page_content=content, metadata={"doc_type": "room_service", "source": source_name}))

    for treatment in data["spa"]:
        content = (
            f"Treatment: {treatment['treatment']}\n"
            f"Duration: {treatment['duration_minutes']} minutes\n"
            f"Price: ₹{treatment['price_inr']}"
        )
        docs.append(Document(page_content=content, metadata={
            "doc_type": "spa_treatment", "name": treatment["treatment"], "source": source_name,
        }))

    facilities = data["facilities"]
    content = (
        f"Pool: {facilities['pool']}\n"
        f"Gym: {facilities['gym']}\n"
        f"Banquet Halls: {facilities['banquet_halls']}\n"
        f"Business Center: {facilities['business_center']}\n"
        f"Airport Transfer: {facilities['airport_transfer']}"
    )
    docs.append(Document(page_content=content, metadata={"doc_type": "facilities", "source": source_name}))

    policies = data["policies"]
    content = (
        f"Check-in Time: {policies['check_in_time']}\n"
        f"Check-out Time: {policies['check_out_time']}\n"
        f"Cancellation Policy: {policies['cancellation_policy']}\n"
        f"Pet Policy: {policies['pet_policy']}\n"
        f"Extra Bed Charge: ₹{policies['extra_bed_charge_inr']}\n"
        f"ID Proof Required: {policies['id_proof_required']}\n"
        f"Minimum Check-in Age: {policies['minimum_check_in_age']}"
    )
    docs.append(Document(page_content=content, metadata={"doc_type": "policy", "source": source_name}))

    for staff in data["staff"]:
        content = f"Name: {staff['name']}\nRole: {staff['role']}\nExperience: {staff['experience_years']} years"
        docs.append(Document(page_content=content, metadata={
            "doc_type": "staff", "name": staff["name"], "source": source_name,
        }))

    location = data["location"]
    content = (
        f"Address: {location['address']}\n"
        f"Distance from Railway Station: {location['distance_from_railway_station_km']} km\n"
        f"Distance from Airport: {location['distance_from_airport_km']} km\n"
        f"Nearby Landmarks: {location['nearby_landmarks']}"
    )
    docs.append(Document(page_content=content, metadata={"doc_type": "location", "source": source_name}))

    docs.append(Document(page_content=f"Parking Information: {data['parking']}", metadata={
        "doc_type": "parking", "source": source_name,
    }))

    contact = data["contact"]
    content = f"Phone: {contact['phone']}\nEmail: {contact['email']}\nWebsite: {contact['website']}"
    docs.append(Document(page_content=content, metadata={"doc_type": "contact", "source": source_name}))

    return docs