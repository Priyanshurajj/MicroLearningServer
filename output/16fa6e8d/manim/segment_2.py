from manim import *

class Segment2Scene(Scene):
    def construct(self):
        # ─── VISUAL STYLE ───────────────────────────────────────────────────
        # Adhering to the strict 4-color palette requirement
        CO2_COLOR = WHITE
        H2O_COLOR = BLUE_C
        PLANT_COLOR = TEAL_C
        TEXT_COLOR = WHITE

        # ─── SETUP ──────────────────────────────────────────────────────────
        # Title
        title = Text("Photosynthesis", font_size=52, color=TEXT_COLOR, weight=BOLD).to_edge(UP, buff=0.5)
        underline = Line(
            title.get_left() + DOWN * 0.2,
            title.get_right() + DOWN * 0.2,
            color=TEXT_COLOR,
            stroke_width=2
        ).align_to(title, LEFT)

        # Stylized Plant
        stem = Line(DOWN * 1.5, UP * 1.0, color=PLANT_COLOR, stroke_width=8)
        
        # A simple V-shape leaf
        leaf1 = VGroup(
            Line(ORIGIN, UL * 0.8),
            Line(ORIGIN, UL * 0.8 + LEFT * 0.6 + DOWN * 0.1)
        ).set_stroke(color=PLANT_COLOR, width=6).move_to(stem.get_center() + LEFT*0.4).shift(UP*0.4)
        
        # A copy rotated for the other side
        leaf2 = leaf1.copy().rotate(PI, axis=UP).move_to(stem.get_center() + RIGHT*0.4).shift(UP*0.4)

        roots = VGroup(*[
            Line(ORIGIN, (DL + i*RIGHT*0.5)*0.6)
            for i in [-1, 0, 1]
        ]).set_stroke(color=PLANT_COLOR, width=4).next_to(stem, DOWN, buff=0)

        plant = VGroup(stem, leaf1, leaf2, roots).center().shift(DOWN*0.5)

        # Molecules (represented as spheres/dots)
        co2_molecules = VGroup(*[
            Dot(radius=0.08, color=CO2_COLOR).move_to(plant.get_top() + UP*1.5 + RIGHT*2.5*(np.random.rand()-0.5))
            for _ in range(5)
        ])
        h2o_molecules = VGroup(*[
            Dot(radius=0.08, color=H2O_COLOR).move_to(plant.get_bottom() + DOWN*1.5 + RIGHT*2.0*(np.random.rand()-0.5))
            for _ in range(5)
        ])

        # Math Labels
        co2_label = MathTex("CO_2", font_size=64, color=CO2_COLOR).next_to(leaf2, UR, buff=0.3)
        h2o_label = MathTex("H_2O", font_size=64, color=H2O_COLOR).next_to(roots, DR, buff=0.3)

        # ─── ANIMATION CHOREOGRAPHY ───────────────────────────────────────
        # 1. OPENING (0-2.2s)
        self.play(Write(title, run_time=1.2))
        self.wait(0.4)
        self.play(FadeIn(underline, shift=RIGHT * 0.5, run_time=0.6))
        self.wait(0.3)

        # 2. BUILDING CONTENT (2.2s-7.4s)
        self.play(Create(plant, run_time=1.2))
        self.wait(0.3)

        # CO2 absorption animation
        co2_animations = [
            m.animate.shift(DOWN * 2.5 + LEFT * (m.get_center()[0] * 0.3)).set_opacity(0)
            for m in co2_molecules
        ]
        self.play(
            LaggedStart(*co2_animations, lag_ratio=0.2, run_time=1.5),
            FadeIn(co2_label, shift=UP * 0.3, run_time=0.8)
        )
        self.wait(0.3)

        # H2O absorption animation
        h2o_animations = [
            m.animate.shift(UP * 2.5 + RIGHT * (m.get_center()[0] * 0.2)).set_opacity(0)
            for m in h2o_molecules
        ]
        self.play(
            LaggedStart(*h2o_animations, lag_ratio=0.2, run_time=1.5),
            FadeIn(h2o_label, shift=DOWN * 0.3, run_time=0.8)
        )

        # 5. CLOSING (7.4s-8.5s)
        self.wait(0.6) # Wait to meet ~8s target duration
        self.play(
            *[FadeOut(mob) for mob in self.mobjects if mob is not None],
            run_time=0.6
        )
        self.wait(0.5)