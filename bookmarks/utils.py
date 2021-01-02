def unique(elements, key):
    return list({key(element): element for element in elements}.values())
