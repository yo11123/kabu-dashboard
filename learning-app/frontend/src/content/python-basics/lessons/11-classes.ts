export const content = `
# クラスとオブジェクト

## クラスの基本

クラスはデータと機能をまとめた設計図です。

\`\`\`python
class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def bark(self):
        return f"{self.name}がワンワン！"

    def info(self):
        return f"{self.name}（{self.age}歳）"

# インスタンスの作成
dog = Dog("ポチ", 3)
print(dog.bark())   # ポチがワンワン！
print(dog.info())   # ポチ（3歳）
\`\`\`

## __init__ メソッド

\`__init__\` はインスタンスが作られるときに自動で呼ばれるコンストラクタです。

\`\`\`python
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height

    def perimeter(self):
        return 2 * (self.width + self.height)

rect = Rectangle(5, 3)
print(f"面積: {rect.area()}")    # 面積: 15
print(f"周長: {rect.perimeter()}")  # 周長: 16
\`\`\`

## 継承

既存のクラスを元に新しいクラスを作れます。

\`\`\`python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "..."

class Cat(Animal):
    def speak(self):
        return f"{self.name}: ニャー"

class Dog(Animal):
    def speak(self):
        return f"{self.name}: ワン"

animals = [Cat("タマ"), Dog("ポチ")]
for animal in animals:
    print(animal.speak())
\`\`\`

## 特殊メソッド

\`\`\`python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"Vector({self.x}, {self.y})"

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __len__(self):
        return int((self.x ** 2 + self.y ** 2) ** 0.5)

v1 = Vector(3, 4)
v2 = Vector(1, 2)
print(v1 + v2)    # Vector(4, 6)
print(len(v1))    # 5
\`\`\`

それでは、演習問題に挑戦しましょう！
`;
