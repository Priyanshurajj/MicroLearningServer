from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # This scene first provides a simple visual metaphor for sunlight
        # being captured by a leaf, then transitions to the chemical equation
        # for photosynthesis, building it step-by-step.

        # Part 1: Visual Metaphor (Sunlight on a leaf)
        leaf = VGroup(
            Ellipse(width=2.5, height=1.5, fill_color=GREEN, fill_opacity=0.8, stroke_width=0).rotate(PI/4),
            Line(start=ORIGIN, end=DOWN*1.5, color=GREEN_E).rotate(PI/4).shift(DOWN*0.5+LEFT*0.5)
        ).move_to(ORIGIN).shift(RIGHT*3)

        sunbeam = Arrow(
            start=UP*3 + LEFT*3,
            end=leaf.get_center(),
            color=YELLOW,
            stroke_width=8,
            buff=0.5,
            max_tip_length_to_length_ratio=0.2
        )

        self.play(FadeIn(leaf, shift=DOWN), run_time=0.75)
        self.play(Create(sunbeam), run_time=0.75)
        self.wait(0.5)
        self.play(FadeOut(leaf, sunbeam), run_time=0.75)
        self.wait(0.25)

        # Part 2: Chemical Equation for Photosynthesis
        # Define the components of the equation using MathTex and Tex
        reactants = MathTex("6CO_2 + 6H_2O").scale(1.2)
        reactants.set_color_by_tex_to_color_map({
            "6CO_2": BLUE,
            "6H_2O": BLUE_D
        })

        arrow = MathTex("\\xrightarrow{}").set_color(WHITE).scale(1.2)
        light_energy = Tex("Light Energy", color=YELLOW).scale(0.8)

        products = MathTex("C_6H_{12}O_6 + 6O_2").scale(1.2)
        products.set_color_by_tex_to_color_map({
            "C_6H_{12}O_6": GREEN,
            "6O_2": RED
        })

        # Animate the equation appearing in sequence
        self.play(Write(reactants))
        self.wait(1)

        arrow.next_to(reactants, RIGHT, buff=0.5)
        light_energy.next_to(arrow, UP, buff=0.2)
        self.play(FadeIn(VGroup(arrow, light_energy)))
        self.wait(1)

        products.next_to(arrow, RIGHT, buff=0.5)
        self.play(Write(products))
        self.wait(1)

        # Group the full equation and center it for a clean final frame
        full_equation = VGroup(reactants, arrow, light_energy, products)
        self.play(full_equation.animate.move_to(ORIGIN))

        self.wait(1)