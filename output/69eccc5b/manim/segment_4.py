from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Set background color to white as per the detailed specification
        self.camera.background_color = WHITE

        # Narration: And here's the magic formula that makes it all happen!
        # Visual Description: The chemical equation appears step-by-step.

        # Define the parts of the photosynthesis equation using MathTex
        # The text color is black to be visible on the white background
        # Using raw strings (r"...") is a best practice for LaTeX to avoid issues with backslashes.
        part1 = MathTex(r"6\text{CO}_2", color=BLACK)
        part2 = MathTex(r"+ 6\text{H}_2\text{O}", color=BLACK)
        arrow = MathTex(r"\rightarrow", color=BLACK)
        part3 = MathTex(r"\text{C}_6\text{H}_{12}\text{O}_6", color=BLACK)
        part4 = MathTex(r"+ 6\text{O}_2", color=BLACK)

        # Group all parts and arrange them horizontally
        equation = VGroup(part1, part2, arrow, part3, part4)
        equation.arrange(RIGHT, buff=0.5).scale(1.5)

        # Animate the appearance of each part of the equation
        self.wait(0.5)

        # Animate 6CO2
        self.play(FadeIn(part1, duration=0.8))
        self.play(Flash(part1, color=YELLOW, line_length=0.2, run_time=0.7))
        self.wait(0.5)

        # Narration: Watch as these ingredients transform inside the plant!
        # Animate + 6H2O
        self.play(FadeIn(part2, duration=0.8))
        self.play(Flash(part2, color=YELLOW, line_length=0.2, run_time=0.7))
        self.wait(0.5)

        # Animate the reaction arrow
        self.play(FadeIn(arrow, duration=0.8))
        self.play(Flash(arrow, color=YELLOW, line_length=0.2, run_time=0.7))
        self.wait(0.5)

        # Animate C6H12O6 (Glucose)
        self.play(FadeIn(part3, duration=0.8))
        self.play(Flash(part3, color=YELLOW, line_length=0.2, run_time=0.7))
        self.wait(0.5)

        # Animate + 6O2 (Oxygen)
        self.play(FadeIn(part4, duration=0.8))
        self.play(Flash(part4, color=YELLOW, line_length=0.2, run_time=0.7))

        # Hold the final frame to let the viewer see the complete equation
        self.wait(1)