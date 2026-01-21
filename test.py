
def check(strings):
	if not strings:
		return "yes"
	stack = []
	for I in strings:
		if I in "([{<":
			stack.append(I)
		else:
			if I==")" and stack[-1]=="(":
				stack.pop()
			elif I=="]" and stack[-1]=="[":
				stack.pop()
			elif I=="}" and stack[-1]=="{":
				stack.pop()
			elif I==">" and stack[-1]=="<":
				stack.pop()
			else:
				return "no"
	return "yes" if not stack else "no"

sample = "([]{<>})"
print(check(sample))