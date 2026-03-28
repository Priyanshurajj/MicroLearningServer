from manim import *
import numpy as np

class Segment3Scene(Scene):
    def construct(self):
        # 1. Setup split screen visual
        divider = Line(UP * 3.5, DOWN * 3.5, color=GRAY, stroke_width=1)
        self.add(divider)

        # 2. Create the leaf cross-section on the left
        leaf_cross_section = RoundedRectangle(
            corner_radius=0.4, height=2.5, width=3.5, color=GREEN_E, fill_opacity=0.3
        )
        
        cells = VGroup()
        for _ in range(25):
            cell = Circle(
                radius=np.random.uniform(0.15, 0.25),
                color=GREEN_D,
                fill_opacity=0.6
            ).move_to(
                leaf_cross_section.get_center() +
                np.array([
                    np.random.uniform(-1.5, 1.5),
                    np.random.uniform(-1.0, 1.0),
                    0
                ])
            )
            cells.add(cell)

        chloroplasts = VGroup()
        for cell in list(cells)[:8]:
            for _ in range(np.random.randint(3, 6)):
                chloro = Dot(
                    color=GREEN_A,
                    radius=0.04
                ).move_to(
                    cell.get_center() + (np.random.rand(3) - 0.5) * 0.25
                )
                chloroplasts.add(chloro)

        leaf_diagram = VGroup(leaf_cross_section, cells, chloroplasts).shift(LEFT * 3.5)
        
        # 3. Define the chemical equation components
        equation = MathTex(
            "6CO_2", "+", "6H_2O", 
            r"\xrightarrow{\text{ {{light energy}} }}", 
            "C_6H_{12}O_6", "+", "6O_2",
            font_size=48
        )
        equation.shift(RIGHT * 3.2)

        reactants = VGroup(equation[0], equation[1], equation[2])
        arrow = VGroup(equation[3])
        products = VGroup(equation[4], equation[5], equation[6])

        # 4. Animation sequence
        self.play(Create(leaf_diagram), run_time=1.5)
        self.wait(0.5)

        # Animate equation appearing step-by-step
        self.play(Write(reactants), run_time=1.0)
        self.wait(0.5)
        self.play(Write(arrow), run_time=1.0)
        self.wait(0.5)
        self.play(Write(products), run_time=1.0)
        self.wait(1.0)

        # Highlight each component with specified colors
        self.play(equation[0].animate.set_color(RED), run_time=0.5)
        self.play(equation[2].animate.set_color(BLUE), run_time=0.5)
        self.play(equation.get_part_by_tex("light energy").animate.set_color(YELLOW), run_time=0.5)
        self.play(equation[4].animate.set_color(GREEN), run_time=0.5)
        self.play(equation[6].animate.set_color(ORANGE), run_time=0.5)

        # Hold the final frame
        self.wait(1)