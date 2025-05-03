from TRASEU.get_route import analyze_route

if __name__ == "__main__":
    result = analyze_route("Z1", "Z4")

    print("Traseu rapid:")
    print(" -> ".join(result['fast_path']))

    print("\nInstrucțiuni complete:")
    for step in result['full_path']:
        print("-", step)

    print("\nDirecții numerice:")
    print(result['directions_numeric'])

    print("\nTaguri utile:")
    for inter, tags in result['possible_tags'].items():
        print(f" - {inter}: {tags}")
