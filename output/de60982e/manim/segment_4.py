from manim import *
import textwrap

class Segment4Scene(Scene):
    def construct(self):
        card = RoundedRectangle(
            corner_radius=0.4,
            width=12,
            height=6,
            fill_color="#0f3460",
            fill_opacity=0.3,
            stroke_color="#e94560",
            stroke_width=2,
        )
        self.add(card)

        title_text = "Photosynthesis: Earth's Breath of Life!"
        content_text = "...then, with a zap of sunlight, they cook up glucose, their food, and release oxygen as a bonus! It's pure magic!"

        wrapped_title = textwrap.fill(title_text, width=30)
        title_obj = Text(wrapped_title, font_size=40, color=WHITE, weight="BOLD")
        title_obj.move_to(ORIGIN).shift(UP * 2)

        accent_bar = Line(LEFT * 3, RIGHT * 3, color="#e94560", stroke_width=4)
        accent_bar.next_to(title_obj, DOWN, buff=0.3)

        wrapped_content = textwrap.fill(content_text, width=40)
        content_obj = Text(wrapped_content, font_size=32, color=LIGHT_GREY, line_spacing=0.8)
        content_obj.next_to(accent_bar, DOWN, buff=0.8)

        self.play(FadeIn(card, shift=UP * 0.3), run_time=0.5)
        self.play(Write(title_obj), run_time=1.0)
        self.play(Create(accent_bar), run_time=0.5)
        self.play(FadeIn(content_obj, shift=UP * 0.3), run_time=1.0)

        self.wait(1.5)
