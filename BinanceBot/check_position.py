import matplotlib.pyplot as plt

file = open('position.log', ('r'))

positions = []

for i in file:
    a = i.split(' ')
    b = {
        'start_epoch': int(a[1][0:-1]),
        'end_epoch': int(a[3][0:-1]),
        'buy_price': float(a[5][0:-1]),
        'sell_price': float(a[7][0:-1]),
        'profit': float(a[9][0:-1]),
    }
    positions.append(b)

balance = 100
equity = [balance]
for j in range(104,len(positions)):
    i = positions[j]
    balance = balance * (1+i['profit'])
    equity.append(balance)

print(equity)
plt.plot(equity)
plt.show()
