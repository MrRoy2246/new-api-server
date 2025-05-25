# s=input()
# i=0
# for letter in s:
#     if i%2==0:
#         print(s[i],end='')
#     i+=1
# -----------------
# x=int(input())

# while x>0:
#     print(x)
#     x-=1
# ------------
# l = [10, 20, 30, 40]
# for i in range(len(l)):
#     print(i, l[i])
# -----------

# n1=int(input())
# n2=int(input())
# tabn1=[]
# tabn2=[]
# for i in range(1, 11):
#     tabn1.append(n1*i)
#     tabn2.append(n2*i)
# res=[]
# for i in range(10):
#     res.append(tabn1[i]-tabn2[i])
# print(*res)

# -------------------
# ll = [[10, 20, 30], [40, 50, 60], [70, 80]]
# for i in ll:
#     for j in i:
#         print(j, end =" ")
#     print()

# ----------------

# n = int(input())


# for i in range (n):
#     for j in range(n-i):
#         print('*' ,end=" ")
#     print()

# ------------



# n = int(input())
# sum=0
# for i in range(1,n+1):
#     sum=sum+i
# print(sum)

# ----------

# n = int(input())
# count=0
# for i in range(1,n+1):
#     if n%i==0:
#         count=count+1
# if count==2:
#     print(True)
# else:
#     print(False)

# ---------
# a=int(input())
# b=int(input())
# operator=int(input())

# if operator==1:
#     print(a+b)
# elif operator==2:
#     print(a-b)
# elif operator==3:
#     print(a*b)
# else:
#     print("Invalid Input")


# n=int(input())
# def firstDigit(n):
#     # Your code here
#     while n>=10:
#         n//=10
#     return n
# a=firstDigit(n)
# print(a)


# def is_prime(x):
#     for i in range(2, x):
#         if x % i == 0:
#             return False
#     return True

# def print_prime_factors(n):
#     for i in range(2, n + 1):
#         if is_prime(i):
#             x = i
#             while n % x == 0:
#                 print(i,end=' ')
#                 x = x * i

# n = 100
# print_prime_factors(n)

