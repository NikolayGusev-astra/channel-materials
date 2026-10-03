"""Ролик по концепции LLM Wiki Андрея Карпатого (gist от 4 апреля 2026).

Тезис, который показывает ролик: RAG переизобретает знание на каждом вопросе,
wiki накапливает. Один и тот же вопрос, два разных исхода.
"""
from manim import *

config.pixel_width = 1920
config.pixel_height = 1080
config.background_color = "#0e0e0e"
config.frame_rate = 60

BLUE3 = "#58C4DD"
YEL3 = "#FC6255"
GRN3 = "#83C167"
GREY_T = "#8A94A6"
FRAME_W, FRAME_H = 14.222, 8.0

DOCS = ["A", "B", "C", "D", "E"]


def fit(m, pad=0.90):
    """Одно масштабирование под оба измерения сразу."""
    m.scale(min(FRAME_W * pad / m.width, FRAME_H * pad / m.height))
    return m


class Title(Scene):
    """Заставка."""

    def construct(self):
        t1 = Text("LLM Wiki", font_size=96, color=WHITE)
        t2 = Text("знание, которое накапливается", font_size=40, color=GREY_T)
        g = fit(VGroup(t1, t2).arrange(DOWN, buff=0.5))
        g.move_to(ORIGIN)
        self.play(FadeIn(t1, shift=UP * 0.3), run_time=0.8)
        self.play(FadeIn(t2), run_time=0.6)
        self.wait(1.4)


class RagRebuilds(Scene):
    """RAG: пять файлов и каждый раз заново собирает ответ."""

    def construct(self):
        head = Text("RAG: ответ собирается заново каждый раз", font_size=40, color=WHITE)
        docs = VGroup(*[
            RoundedRectangle(
                corner_radius=0.15, width=1.5, height=1.9,
                stroke_color=GREY_B, stroke_width=3,
            ).move_to(LEFT * 5 + RIGHT * i * 2.5)
            for i in range(len(DOCS))
        ])
        labels = VGroup(*[
            Text(d, font_size=44, color=GREY_T).move_to(docs[i])
            for i, d in enumerate(DOCS)
        ])
        self.play(Write(head), run_time=0.7)
        self.play(LaggedStart(*[Create(d) for d in docs], lag_ratio=0.12), run_time=0.9)
        self.add(labels)

        for round_no in (1, 2):
            ans = fit(
                RoundedRectangle(
                    corner_radius=0.15, width=5.6, height=1.2,
                    stroke_color=YEL3, stroke_width=4,
                ),
                pad=0.5,
            )
            ans.to_edge(DOWN, buff=1.1)
            tag = Text("сборка ответа %d" % round_no, font_size=30, color=YEL3)
            tag.next_to(ans, DOWN, buff=0.25)

            arrows = VGroup(*[
                Arrow(d.get_top(), ans.get_top(), buff=0.2, color=YEL3,
                      stroke_width=2, max_tip_length_to_length_ratio=0.12)
                for d in docs
            ])
            self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.08), run_time=0.7)
            self.play(FadeIn(ans), FadeIn(tag), run_time=0.4)
            self.wait(0.5)
            self.play(
                *[FadeOut(m) for m in (arrows, ans, tag)],
                run_time=0.35,
            )
        note = Text("ничего не сохранилось", font_size=34, color=YEL3)
        note.to_edge(DOWN, buff=0.7)
        self.play(FadeIn(note), run_time=0.4)
        self.wait(0.6)


class WikiAccumulates(Scene):
    """Wiki: те же пять файлов, между ними появляются связи."""

    def construct(self):
        head = Text("Wiki: файлы связаны между собой", font_size=40, color=WHITE)
        docs = VGroup(*[
            RoundedRectangle(
                corner_radius=0.15, width=1.5, height=1.9,
                stroke_color=BLUE3, stroke_width=3,
            ).move_to(LEFT * 5 + RIGHT * i * 2.5)
            for i in range(len(DOCS))
        ])
        labels = VGroup(*[
            Text(d, font_size=44, color=WHITE).move_to(docs[i])
            for i, d in enumerate(DOCS)
        ])
        self.play(Write(head), run_time=0.7)
        self.play(LaggedStart(*[Create(d) for d in docs], lag_ratio=0.12), run_time=0.9)
        self.add(labels)

        links = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 2), (1, 4)]
        arrows = VGroup(*[
            CurvedArrow(
                docs[a].get_right(), docs[b].get_left(),
                angle=-0.5 if b > a else 0.5,
                color=GRN3, stroke_width=3,
                tip_length=0.22,
            )
            for a, b in links
        ])
        self.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.10), run_time=1.2)

        acc = Text("знание сложилось один раз", font_size=34, color=GRN3)
        acc.to_edge(DOWN, buff=0.7)
        self.play(FadeIn(acc), run_time=0.5)
        self.wait(0.9)


class SecondQuestion(Scene):
    """Тот же вопрос второй раз: wiki отвечает сразу, RAG собирает заново."""

    def construct(self):
        q1 = Text("как связаны A и C?", font_size=38, color=WHITE)
        q2 = Text("как связаны B и D?", font_size=38, color=WHITE)
        left = fit(VGroup(q1, q2).arrange(DOWN, buff=0.8), pad=0.5)
        left.move_to(ORIGIN)
        self.play(FadeIn(q1), run_time=0.5)
        self.wait(0.6)
        self.play(FadeIn(q2), run_time=0.5)
        self.wait(0.7)

        wiki = Text("wiki: путь уже есть", font_size=34, color=GRN3)
        rag = Text("RAG: нужен новый поиск", font_size=34, color=YEL3)
        row = VGroup(wiki, rag).arrange(RIGHT, buff=2.2).scale_to_fit_width(12)
        row.to_edge(DOWN, buff=1.2)
        self.play(FadeIn(wiki, shift=UP * 0.2), run_time=0.5)
        self.play(FadeIn(rag, shift=UP * 0.2), run_time=0.5)
        self.wait(1.0)


class WhoWrites(Scene):
    """Кто пишет wiki: не человек."""

    def construct(self):
        human = VGroup(
            Circle(radius=0.35, color=GREY_T, stroke_width=3).shift(UP * 0.5),
            Line(LEFT * 0.45, RIGHT * 0.45, color=GREY_T, stroke_width=5).shift(DOWN * 0.4),
        )
        agent = VGroup(
            Circle(radius=0.35, color=BLUE3, stroke_width=3).shift(UP * 0.5),
            Line(LEFT * 0.45, RIGHT * 0.45, color=BLUE3, stroke_width=5).shift(DOWN * 0.4),
        )
        gap = fit(VGroup(human, agent).arrange(RIGHT, buff=3.0), pad=0.35)
        gap.move_to(ORIGIN)

        left_t = Text("человек", font_size=36, color=GREY_T).next_to(human, DOWN, buff=0.4)
        right_t = Text("LLM", font_size=36, color=BLUE3).next_to(agent, DOWN, buff=0.4)

        arrow = Arrow(agent.get_left(), human.get_right(), buff=0.3, color=BLUE3,
                      stroke_width=5, max_tip_length_to_length_ratio=0.1)
        arrow_t = Text("пишет и поддерживает wiki", font_size=30, color=WHITE)
        arrow_t.next_to(arrow, UP, buff=0.3)

        self.play(FadeIn(human), FadeIn(left_t), run_time=0.6)
        self.play(GrowArrow(arrow), FadeIn(arrow_t), run_time=0.6)
        self.play(FadeIn(agent), FadeIn(right_t), run_time=0.6)

        note = Text("человек ищет источники и задаёт вопросы", font_size=34, color=WHITE)
        note.to_edge(DOWN, buff=0.9)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(1.2)


class Outro(Scene):
    """Финал: три строки оценочной."""

    def construct(self):
        lines = VGroup(
            Text("wiki пишет LLM, а не человек", font_size=42, color=WHITE),
            Text("знание собирается один раз", font_size=42, color=WHITE),
            Text("и остаётся связанным", font_size=42, color=GRN3),
        ).arrange(DOWN, buff=0.6, aligned_edge=LEFT)
        g = fit(lines)
        g.move_to(ORIGIN)
        self.play(LaggedStart(*[FadeIn(l, shift=RIGHT * 0.3) for l in lines], lag_ratio=0.35),
                  run_time=2.0)
        self.wait(1.4)
