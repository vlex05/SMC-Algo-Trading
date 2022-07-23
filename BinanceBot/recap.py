
file = open("position.log",'r')
out = []
for i in file:
    a = i.split(' ')
    out.append(float(a[9][:-1]))

start = 100.0

for i in out:
    start = start*(1+i)
    # print(start)

print("final: " + str(start))

