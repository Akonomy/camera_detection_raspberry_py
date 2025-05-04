#!/usr/bin/env python3
# Stil C-like: se folosesc doar structuri de bază, bucle for explicite și operații bitwise.

def encode_message(input_vector):

    # Calculăm lungimea vectorului (stil C-like)
    n = 0
    while n < len(input_vector):
        n += 1
    if n > 10:
        raise ValueError("Lungimea maximă admisă este 10 elemente.")

    packed = 0
    i = 0
    while i < n:
        val = input_vector[i]
        # Verificăm dacă valoarea este între 0 și 7
        if val < 0 or val > 7:
            raise ValueError("Valorile trebuie să fie între 0 și 7.")
        packed |= (val & 0x07) << (3 * i)
        i += 1

    # Cheia = suma elementelor mod 256
    key = 0
    i = 0
    while i < n:
        key = (key + input_vector[i]) & 0xFF
        i += 1

    # Extragem cei 4 octeți + XOR
    vec = [0] * 4
    i = 0
    while i < 4:
        vec[i] = ((packed >> (8 * i)) & 0xFF) ^ key
        i += 1

    data1 = n & 0xFF
    data2 = key & 0xFF
    return (6, data1, data2, vec)



def decode_message(encoded_tuple):
    cmd_type, data1, key, vec = encoded_tuple

    if cmd_type != 6:
        raise ValueError("Comanda trebuie să fie de tip 6.")
    if data1 > 10:
        raise ValueError("Lungimea nu poate depăși 10.")
    if len(vec) != 4:
        raise ValueError("Vectorul trebuie să aibă exact 4 octeți.")

    # Eliminăm XOR
    data = [0] * 4
    i = 0
    while i < 4:
        data[i] = vec[i] ^ key
        i += 1

    # Reasamblăm în 32 de biți (little-endian)
    packed = 0
    i = 0
    while i < 4:
        packed |= data[i] << (8 * i)
        i += 1

    # Extragem valorile (3 biți fiecare)
    output_vector = [0] * data1
    i = 0
    while i < data1:
        output_vector[i] = (packed >> (3 * i)) & 0x07
        i += 1

    return output_vector

def main():
    vectors = [
        [0, 1, 2, 3, 4, 5, 6, 7, 0, 1],
        [3, 2, 1],
        [7, 6, 0, 1, 4],
    ]

    for vec in vectors:
        encoded = encode_message(vec)
        print("Original:", vec)
        print("Encoded:", encoded)
        decoded = decode_message(encoded)
        print("Decoded:", decoded)
        print("Match:", decoded == vec)
        print("---")

if __name__ == "__main__":
    main()
