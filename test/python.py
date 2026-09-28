def print_diamond_pattern(n):
    print("=== Diamond Pattern ===")
    for i in range(n):
        print(" " * (n - i - 1) + "* " * (i + 1))
    for i in range(n - 2, -1, -1):
        print(" " * (n - i - 1) + "* " * (i + 1))

def print_number_pyramid(n):
    print("\n=== Number Pyramid ===")
    for i in range(1, n + 1):
        # spaces
        print(" " * (n - i), end="")
        # increasing numbers
        for j in range(1, i + 1):
            print(j, end="")
        # decreasing numbers
        for j in range(i - 1, 0, -1):
            print(j, end="")
        print()

if __name__ == "__main__":
    print_diamond_pattern(5)
    print_number_pyramid(5)
