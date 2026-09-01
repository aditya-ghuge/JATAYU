def calculate_risk(smoke, temperature, gas):

    if smoke >= 80 or temperature >= 70 or gas >= 80:
        return "RED"

    elif smoke >= 50 or temperature >= 50 or gas >= 50:
        return "ORANGE"

    elif smoke >= 25 or temperature >= 35 or gas >= 25:
        return "YELLOW"

    return "GREEN"