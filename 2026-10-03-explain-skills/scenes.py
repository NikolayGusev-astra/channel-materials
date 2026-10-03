"""Все сцены статьи одним файлом - чтобы отрендерить кадры для иллюстраций.

Каждая сцена соответствует абзацу статьи: синус с бегунком, окружность на
числовой плоскости, комплексная плоскость, бинарный поиск, сортировка, граф,
матрица и проверка формул после установки LaTeX.
"""
from manim import *

config.pixel_width = 1920
config.pixel_height = 1080
config.background_color = "#0e0e0e"
config.frame_rate = 60

BLUE3 = "#58C4DD"
YEL3 = "#FC6255"
GRN3 = "#83C167"

FRAME_W, FRAME_H = 14.222, 8.0

TRACK = ValueTracker(0.0)


class Sinus(Scene):
    """Анимация синусоиды с бегунком и живой подписью."""

    def construct(self):
        ax = Axes(
            x_range=[-3.2, 3.2, 1],
            y_range=[-2, 2, 1],
            x_length=9.5,
            y_length=6,
            axis_config={"color": GREY_B, "include_tip": False},
        )
        curve = ax.plot(lambda x: np.sin(x), color=BLUE3, stroke_width=5)
        self.play(Create(ax), run_time=1.0)
        self.play(Create(curve), run_time=1.8)

        dot = always_redraw(
            lambda: Dot(color=YEL3, radius=0.07).move_to(
                curve.point_from_proportion(TRACK.get_value())
            )
        )
        label = always_redraw(
            lambda: Text(f"x = {TRACK.get_value():.2f}", font_size=34, color=WHITE)
            .next_to(ax, DOWN, buff=0.35)
        )
        self.add(dot, label)
        self.play(TRACK.animate.set_value(1.0), run_time=3.0, rate_func=linear)
        self.wait(1.0)


class CirclePlane(Scene):
    """Окружность на числовой плоскости, подпись с формулой юникодом."""

    def construct(self):
        ax = NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            x_length=11,
            y_length=7,
            axis_config={"color": GREY_B, "include_ticks": True},
        )
        circ = Circle(radius=2 * ax.c2p(1, 0)[0], stroke_color=BLUE3, stroke_width=5)
        circ.move_to(ax.c2p(1, 1))
        cap = Text("круг: (x-1)^2 + (y-1)^2 = 4", font_size=40, color=WHITE)
        g = VGroup(circ, cap).arrange(DOWN, buff=0.6)
        # один вызов, запас 10% по каждой оси
        g.scale(min(FRAME_W * 0.90 / g.width, FRAME_H * 0.90 / g.height))
        self.add(ax)
        self.play(Create(circ), run_time=1.6)
        self.play(FadeIn(cap), run_time=0.6)
        self.wait(1.2)


class CplxScene(Scene):
    """Сложное число на плоскости, радиус и аргумент.

    Имя класса не должно совпадать с импортом ComplexPlane из движка:
    перекрытие даёт "Scene.__init__() got an unexpected keyword argument x_range".
    """

    def construct(self):
        plane = ComplexPlane(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=6.7,
            axis_config={"color": GREY_B},
        )
        z = Dot(color=YEL3, radius=0.08).move_to(plane.c2p(1.5, 1.2))
        u = Arrow(plane.c2p(0, 0), z.get_center(), buff=0, color=GRN3, stroke_width=6)
        ang = Angle(
            Line(plane.c2p(1, 0), z.get_center()),
            Line(plane.c2p(0, 0), z.get_center()),
            radius=1.1,
            color=YEL3,
        )
        lab = Text("z = 1.5 + 1.2i", font_size=40, color=WHITE).move_to(plane.c2p(0, -2.4))
        self.add(plane)
        self.play(Create(u), Create(ang), run_time=1.8)
        self.play(FadeIn(lab), run_time=0.6)
        self.wait(1.0)


ARR = [3, 7, 12, 18, 23, 31, 44, 57, 69, 81]
LO = ValueTracker(0.0)
HI = ValueTracker(9.0)


class BinarySearch(Scene):
    """Бинарный поиск: две рамки границ и подсветка найденного элемента."""

    def construct(self):
        cells = VGroup(*[
            Square(side_length=1.1, stroke_color=GREY_B, stroke_width=3)
            .move_to(LEFT * 5 + RIGHT * i * 1.3)
            for i in range(len(ARR))
        ])
        nums = VGroup(*[
            Text(str(v), font_size=38).move_to(c) for c, v in zip(cells, ARR)
        ])
        self.add(cells, nums)
        lo_box = always_redraw(
            lambda: SurroundingRectangle(cells[int(LO.get_value())], color=GRN3, buff=0.08)
        )
        hi_box = always_redraw(
            lambda: SurroundingRectangle(cells[int(HI.get_value())], color=BLUE3, buff=0.08)
        )
        self.add(lo_box, hi_box)
        self.play(LO.animate.set_value(3.0), HI.animate.set_value(7.0), run_time=1.5)
        self.play(Indicate(cells[6], color=YEL3), run_time=1.2)
        self.wait(1.0)


class SortScene(Scene):
    """Сортировка: элементы едут на новые места, порядок задан индексами.

    order[i] - индекс КУДА едет элемент с позиции i. Проверено на кадре:
    5 2 9 1 7 -> 1 2 5 7 9. Прежний вариант [4,1,3,0,2] давал 1 2 7 9 5,
    то есть неотсортированный результат - опечатка была не видна без кадра.
    """

    def construct(self):
        order = [2, 1, 4, 0, 3]
        base = [5, 2, 9, 1, 7]
        cells = VGroup(*[
            Square(side_length=1.1, stroke_color=GREY_B, stroke_width=3)
            .move_to(LEFT * 3.2 + RIGHT * i * 1.3)
            for i in range(5)
        ])
        nums = VGroup(*[Text(str(v), font_size=40).move_to(c) for c, v in zip(cells, base)])
        self.add(cells, nums)
        self.play(
            LaggedStart(*[
                nums[i].animate.move_to(cells[j]).set_color(YEL3)
                for i, j in enumerate(order)
            ], lag_ratio=0.2),
            run_time=2.4,
        )
        self.play(nums.animate.set_color(WHITE), run_time=0.5)
        self.wait(1.0)


EDGES = [(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)]
POS = {0: (-3, 1, 0), 1: (0, 2, 0), 2: (3, 1, 0), 3: (4.5, -1.5, 0), 4: (1.5, -2.5, 0)}


class GraphScene(Scene):
    """Граф: рёбра рисуются первыми, вершины и подписи - поверх."""

    def construct(self):
        dots = VGroup(*[
            Dot(color=BLUE3, radius=0.12).move_to(RIGHT * x + UP * y + IN * z)
            for (x, y, z) in POS.values()
        ])
        arrows = VGroup(*[
            Arrow(
                dots[a].get_center(),
                dots[b].get_center(),
                buff=0.25,
                color=GREY_B,
                stroke_width=4,
                max_tip_length_to_length_ratio=0.12,
            )
            for a, b in EDGES
        ])
        labs = VGroup(*[
            Text(str(k), font_size=32, color=WHITE)
            .move_to(d.get_center() + UP * 0.45 + LEFT * 0.35)
            for k, d in zip(POS.keys(), dots)
        ])
        self.play(Create(arrows), run_time=1.6)
        self.add(dots, labs)
        self.wait(1.0)


class MatrixTex(Scene):
    """Матрица настоящим TeX - то, что не собиралось на Text."""

    def construct(self):
        m = MathTex(r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}", color=BLUE3)
        m.scale(5.5 / m.height).move_to(ORIGIN)
        self.play(Write(m), run_time=1.4)
        self.wait(1.2)


class TexFormulas(Scene):
    """Проверка формул после установки LaTeX: Эйлер, интеграл, матрица."""

    def construct(self):
        head = Text("Проверка TeX после установки MiKTeX", font_size=40, color=WHITE)
        eq = MathTex(r"e^{i\pi} + 1 = 0", color=BLUE3)
        integral = MathTex(r"\int_a^b f(x)\,dx = F(b) - F(a)", color=YEL3)
        matrix = MathTex(r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}", color=GRN3)
        # Масштабировать ОДИН раз. Цепочка scale_to_fit_width(...).scale_to_fit_height(...)
        # увеличивает оба измерения: группа была 11.712 x 5.560, первый вызов растянул
        # до 13, второй до 7.2 по высоте, на выходе ширина 15.168 при кадре 14.222 -
        # контент уезжал за кадр и буквы на краях срезало.
        g = VGroup(head, eq, integral, matrix).arrange(DOWN, buff=0.7)
        if g.width / FRAME_W > g.height / FRAME_H:
            g.scale(FRAME_W * 0.90 / g.width)
        else:
            g.scale(FRAME_H * 0.90 / g.height)
        g.move_to(ORIGIN)
        self.add(g)
        self.wait(0.2)
