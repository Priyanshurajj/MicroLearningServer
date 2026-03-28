from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Define MathTex elements for the chemical equation
        reactants = MathTex(
            "6", "CO_2", "+", "6", "H_2O", "+", r"\text{Light Energy}",
        ).set_color_by_tex_to_color_map({
                "CO_2": BLUE,
                "H_2O": YELLOW,
                r"\text{Light Energy}": GOLD,
            })

        arrow = MathTex(r"\rightarrow", color=WHITE).scale(1.5)

        products = MathTex(
            "C_6H_{12}O_6", "+", "6O_2",
        ).set_color_by_tex_to_color_map({
                "C_6H_{12}O_6": GREEN,
                "O_2": RED,
            })

        # Position the elements on the screen
        reactants.to_edge(LEFT, buff=0.5)
        arrow.next_to(reactants, RIGHT, buff=0.7)
        products.next_to(arrow, RIGHT, buff=0.7)

        # Animation: Reactants appear
        self.play(Write(reactants), run_time=1.5)
        self.wait(0.5)

        # Animation: Arrow is written
        self.play(Write(arrow), run_time=1.0)
        self.wait(0.5)

        # Animation: Products appear
        self.play(Write(products), run_time=1.5)
        self.wait(1.0)

        # Animation: Sugar molecule is highlighted
        sugar_molecule = products.get_part_by_tex("C_6H_{12}O_6")
        self.play(
            Indicate(sugar_molecule, color="#99FF99", scale_factor=1.2),
            run_time=1.5
        )
        self.wait(0.5)

        # Animation: Oxygen molecules float away
        oxygen_text = products.get_part_by_tex("O_2")
        
        oxygen_bubbles = VGroup(*[
            Dot(
                point=oxygen_text.get_center() + RIGHT*x + UP*y,
                radius=0.06,
                color="#EF5350"
            )
            for x in [-0.2, 0.2, -0.1]
            for y in [0.1, 0.3, 0.5]
        ])

        # Replace the oxygen text with bubbles
        self.play(
            ReplacementTransform(VGroup(products.get_part_by_tex("6"), oxygen_text), oxygen_bubbles),
            run_time=1.0
        )

        # Animate the bubbles floating away
        bubble_animation = AnimationGroup(
            *[FadeOut(dot, shift=UP * 1.5) for dot in oxygen_bubbles],
            lag_ratio=0.2
        )
        
        self.play(
            bubble_animation,
            run_time=2.0
        )

        self.wait(1)