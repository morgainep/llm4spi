import myconfig

def foo():
    print(f">>> {myconfig.CONFIG_USE_SECOND_TESTSUITE_AS_BASETESTS_TOO}")


# Post-condition: r should be True if and only if there exist two distinct indices i and j such that
# # z[i] + z[j] > a.
def post_HE0(r,z,a):
   def exists_two_elements_with_sum_greater_than_a(z, a):
      for i in range(len(z)):
        for j in range(i + 1, len(z)):
          if z[i] + z[j] > a:
            return True
      return False
   
   return r == exists_two_elements_with_sum_greater_than_a(z, a)

o = post_HE0(*[False, [3550], 3550])
print(f" o = {o}")
o = post_HE0(*[False, [False, True, False, False], True])
print(f" o = {o}")

         