from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Create all the mathematical and text objects for the equation
        co2_obj = MathTex("6\\text{CO}_2", color=BLUE)
        plus1_obj = MathTex("+", color=WHITE)
        h2o_obj = MathTex("6\\text{H}_2\\text{O}", color=WHITE)
        arrow_obj = MathTex("\\rightarrow", color=GREY_BROWN)
        light_energy_obj = Tex("Light Energy", color=YELLOW).scale(0.8)
        glucose_obj = MathTex("\\text{C}_6\\text{H}_{12}\\text{O}_6", color=GREEN)
        plus2_obj = MathTex("+", color=WHITE)
        o2_obj = MathTex("6\\text{O}_2", color=RED)

        # Group the main equation components and arrange them horizontally
        equation_line = VGroup(
            co2_obj, plus1_obj, h2o_obj, arrow_obj, glucose_obj, plus2_obj, o2_obj
        ).arrange(RIGHT, buff=0.25)

        # Position the "Light Energy" text above the arrow
        light_energy_obj.next_to(arrow_obj, UP, buff=0.15)

        # Group the entire equation and center it on the screen
        full_equation = VGroup(equation_line, light_energy_obj).center()

        # Animation sequence for building the equation
        # "Carbon dioxide..."
        self.play(Write(co2_obj), run_time=0.7)
        self.play(Indicate(co2_obj, scale_factor=1.2, color=BLUE), run_time=0.8)
        self.wait(0.2)

        # "...plus water..."
        self.play(Write(plus1_obj), run_time=0.5)
        self.play(Write(h2o_obj), run_time=0.7)
        self.play(Indicate(h2o_obj, scale_factor=1.2, color=WHITE), run_time=0.8)
        self.wait(0.2)

        # "...with light energy..."
        self.play(Write(arrow_obj), run_time=0.7)
        self.play(FadeIn(light_energy_obj, shift=UP * 0.2), run_time=0.7)
        self.play(Indicate(VGroup(arrow_obj, light_energy_obj), scale_factor=1.1, color=YELLOW), run_time=1.0)
        self.wait(0.2)

        # "...creates glucose..."
        self.play(Write(glucose_obj), run_time=1.0)
        self.play(Indicate(glucose_obj, scale_factor=1.2, color=GREEN), run_time=0.8)
        self.wait(0.2)

        # "...and oxygen..."
        self.play(Write(plus2_obj), run_time=0.5)
        self.play(Write(o2_obj), run_time=0.7)
        self.play(Indicate(o2_obj, scale_factor=1.2, color=RED), run_time=0.8)

        # Hold on the final equation
        self.wait(2.5)