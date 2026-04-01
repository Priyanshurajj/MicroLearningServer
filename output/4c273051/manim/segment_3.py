from manim import *
import random
import numpy as np

class Segment3Scene(Scene):
    def construct(self):
        # Create a microscopic background of plant cells and chloroplasts
        cells = VGroup()
        # Use a larger range to fill the screen even on wider aspect ratios
        for i in range(-10, 11):
            for j in range(-6, 7):
                hexagon = RegularPolygon(n=6, radius=0.8, color=GREEN_E, fill_opacity=0.2, stroke_width=1.5)
                # Stagger rows for a honeycomb pattern
                x_pos = i * hexagon.width * 0.75
                y_pos = j * hexagon.height + (i % 2) * hexagon.height / 2
                hexagon.move_to([x_pos, y_pos, 0])
                cells.add(hexagon)
                # Add chloroplasts inside each cell
                for _ in range(random.randint(3, 6)):
                    chloroplast = Dot(
                        point=hexagon.get_center() + np.random.uniform(-0.3, 0.3, 3) * np.array([1, 1, 0]),
                        radius=random.uniform(0.04, 0.08),
                        color=GREEN_C
                    )
                    cells.add(chloroplast)
        
        cells.set_z_index(-10)
        self.add(cells)

        # Animate "Chloroplasts" text
        chloroplasts_text = Tex("Chloroplasts", color=GREEN_A)
        chloroplasts_text.scale(1.5).to_edge(UP)
        self.play(FadeIn(chloroplasts_text), run_time=1.0)
        self.wait(1.0)
        self.play(FadeOut(chloroplasts_text), run_time=1.0)
        self.wait(0.5)

        # Create MathTex elements for the chemical equation
        co2 = MathTex("6CO_2", color=RED_C).scale(1.8)
        plus = MathTex("+", color=WHITE).scale(1.8)
        h2o = MathTex("6H_2O", color=BLUE_D).scale(1.8)
        
        # Arrange the elements in a group to center them easily
        equation = VGroup(co2, plus, h2o).arrange(RIGHT, buff=0.5)
        equation.center()

        # Animate the chemical components sequentially
        self.play(Write(co2), run_time=1.0)
        self.wait(0.5)
        
        self.play(Write(plus), run_time=1.0)
        self.wait(0.5)

        self.play(Write(h2o), run_time=1.0)

        self.wait(1)