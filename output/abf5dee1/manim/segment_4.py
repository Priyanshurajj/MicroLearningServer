from manim import *
import random

class Segment4Scene(Scene):
    def construct(self):
        # Helper function to create an O2 molecule visual
        def create_o2_molecule():
            o1 = Dot(radius=0.08, color=RED)
            o2 = Dot(radius=0.08, color=RED).next_to(o1, RIGHT, buff=0.08)
            bond = Line(o1.get_center(), o2.get_center(), stroke_width=2, color=WHITE)
            return VGroup(o1, o2, bond)

        # 1. Leaf Diagram is present
        leaf = Polygon(
            [-2, 0, 0], [-1, 1.2, 0], [0, 1.8, 0], [1.5, 1.6, 0],
            [2.5, 0, 0], [1.5, -1.6, 0], [0, -1.8, 0], [-1, -1.2, 0],
            color=GREEN_E, fill_opacity=0.9
        ).scale(1.1).shift(UP * 0.5)
        leaf.set_stroke(width=4, color=GREEN_D)
        
        self.play(Create(leaf), run_time=1.0)

        # 2. Sun rays hit the leaf
        sun_rays = VGroup()
        for i in range(4):
            ray = Line(
                start=UP * 4 + LEFT * (4 + i*0.5),
                end=leaf.get_center() + RIGHT * (i*0.3 - 0.45) + DOWN * 0.5,
                stroke_width=8,
                color=YELLOW
            )
            sun_rays.add(ray)
        
        self.play(LaggedStart(*[Create(ray) for ray in sun_rays], lag_ratio=0.1), run_time=1.0)

        # 3. Chemical equation appears
        equation = MathTex(
            "6CO_2", "+", "6H_2O", "+", r"\text{Light Energy}",
            r"\rightarrow",
            "C_6H_{12}O_6", "+", "6O_2",
            color=WHITE
        ).scale(0.9).to_edge(DOWN, buff=0.7)

        glucose_tex = equation.get_part_by_tex("C_6H_{12}O_6")
        oxygen_tex = equation.get_part_by_tex("6O_2")

        self.play(Write(equation), run_time=1.5)
        self.wait(0.2)

        # 4. Reaction unfolds: products are highlighted
        self.play(FadeOut(sun_rays), run_time=0.5)

        # Highlight Glucose
        glucose_molecule = RegularPolygon(n=6, color=GREEN_D, fill_opacity=1).scale(0.4)
        glucose_molecule.next_to(glucose_tex, UP, buff=0.4)
        
        self.play(
            Indicate(glucose_tex, color=GREEN, scale_factor=1.2),
            FadeIn(glucose_molecule, scale=0.5),
            run_time=1.2
        )
        self.wait(0.3)

        # Highlight Oxygen and show molecules appearing
        self.play(Indicate(oxygen_tex, color=RED, scale_factor=1.2), run_time=1.0)

        # 5. Oxygen molecules are created and released
        o2_molecules = VGroup(*[create_o2_molecule().scale(0.7) for _ in range(3)])
        o2_molecules.arrange(buff=0.1).move_to(leaf.get_center())

        self.play(LaggedStart(*[FadeIn(o2) for o2 in o2_molecules], lag_ratio=0.2), run_time=0.5)
        
        # Animate oxygen molecules moving away from the leaf
        self.play(
            LaggedStart(
                o2_molecules[0].animate.shift(UP * 1.5 + RIGHT * 2.5),
                o2_molecules[1].animate.shift(UP * 0.5 + RIGHT * 3.0),
                o2_molecules[2].animate.shift(UP * -0.5 + RIGHT * 2.8),
                lag_ratio=0.1,
                run_time=1.3
            ),
            FadeOut(glucose_molecule)
        )

        self.wait(1)