#!/usr/bin/env python3
# Stil C-like: se folosesc doar structuri de bază, bucle for explicite și operații bitwise.

def encode_message(input_vector):
    # Calculăm lungimea vectorului (stil C-like, folosind buclă explicită)
    n = 0
    while n < len(input_vector):
        n += 1
    # Verificăm dacă lungimea nu depășește 16 elemente
    if n > 16:
        raise ValueError("Lungimea maximă admisă este 16 elemente.")
    
    # Inițializăm variabila de 32 de biți pentru bit-packing
    packed = 0
    i = 0
    while i < n:
        val = input_vector[i]
        # Verificăm dacă valoarea este validă (între 1 și 4)
        if val < 1 or val > 4:
            raise ValueError("Valorile trebuie să fie între 1 și 4.")
        # Mapăm valorile: 1->0, 2->1, 3->2, 4->3 (pentru a folosi 2 biți)
        val = val - 1
        # Inserăm valoarea în packed la poziția 2*i (stil bitwise, little-endian)
        packed |= (val & 0x03) << (2 * i)
        i += 1

    # Calculăm cheia: suma elementelor originale modulo 256
    key = 0
    i = 0
    while i < n:
        key = (key + input_vector[i]) & 0xFF
        i += 1

    # Extragem cei 4 octeți din valoarea de 32 de biți (presupunem little-endian)
    vec = [0, 0, 0, 0]
    i = 0
    while i < 4:
        vec[i] = (packed >> (8 * i)) & 0xFF
        i += 1

    # data1 este lungimea vectorului, data2 este cheia
    data1 = n & 0xFF
    data2 = key & 0xFF

    # Returnăm tuple-ul final cu cmd type 5 la început
    return (5, data1, data2, vec)





    

def decode_vector(encoded):
    # Se așteaptă ca encoded să fie o listă de 6 octeți.
    if not (len(encoded) == 6):
        raise ValueError("Vectorul codificat trebuie să aibă 6 octeți.")
    
    # Se extrag lungimea și cheia
    n = encoded[0]
    key = encoded[1]

    # Se recuperează cei 4 octeți și se anulează XOR-ul
    data = [0, 0, 0, 0]
    i = 0
    while i < 4:
        data[i] = encoded[2 + i] ^ key
        i += 1

    # Reasamblăm valoarea de 32 de biți
    packed = 0
    i = 0
    while i < 4:
        packed |= data[i] << (8 * i)
        i += 1

    # Extragem elementele: fiecare ocupă 2 biți
    output_vector = [0] * n  # alocăm un vector de lungime n
    i = 0
    while i < n:
        # Extragem 2 biți pentru elementul i
        val = (packed >> (2 * i)) & 0x03
        # Convertim înapoi la intervalul 1-4
        output_vector[i] = val + 1
        i += 1

    return output_vector

# Modul de test:
def main():
    # Exemple de vectori de test (valorile sunt între 1 și 4)
    test_vectors = [
        [1, 2, 3, 4, 2, 1, 1, 1, 2],
        [1, 1, 1, 2, 3, 3, 4, 4, 4],
        [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]  # 16 elemente
    ]

    i = 0
    while i < len(test_vectors):
        vec = test_vectors[i]
        print("Vector original:", vec)
        encoded = encode_vector(vec)
        print("Vector codificat (6 octeți):", encoded)
        decoded = decode_vector(encoded)
        print("Vector decodificat:", decoded)
        if vec == decoded:
            print("Test OK.")
        else:
            print("Eroare la test.")
        print("-------------------------------------------------")
        i += 1

if __name__ == '__main__':
    main()
