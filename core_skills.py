import random
rand_list = []

for _ in range(10):
    rand_list.append(random.randint(1, 20))

print(rand_list)

list_comprehension_below_10 = []

for number in rand_list:
    if number < 10:
        list_comprehension_below_10.append(number)

print(list_comprehension_below_10)

list_comprehension_below_10_filter = []

def get_below_10(number):
    if number < 10:
        return number
    
list_comprehension_below_10_filter = filter(get_below_10, rand_list)
print(list(list_comprehension_below_10_filter))