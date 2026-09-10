def fibonacci(n):
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[-1] + fib[-2])
    return fib[:n]

if __name__ == "__main__":
    n = 10
    print(f"First {n} numbers of the Fibonacci sequence:")
    print(fibonacci(n))
