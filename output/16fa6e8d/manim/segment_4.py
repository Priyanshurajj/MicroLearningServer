from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Set up a subtle grid background for a scientific feel
        grid = NumberPlane(
            background_line_style={
                "stroke_color": BLUE_E,
                "stroke_opacity": 0.15
            }
        )
        self.add(grid)

        # 1. OPENING: Title and underline
        title = Tex(r"\textbf{The Magic Equation}", font_size=52).to_edge(UP, buff=0.8)
        underline = Line(
            title.get_left() + DOWN * 0.2,
            title.get_right() + DOWN * 0.2,
            color=WHITE,
            stroke_width=2
        )

        self.play(Write(title, run_time=1.2))
        self.wait(0.4)
        self.play(FadeIn(underline, shift=RIGHT * 0.5, run_time=0.6))
        self.wait(0.3)

        # 2. BUILDING CONTENT: The Photosynthesis Equation
        # Use substrings in MathTex to easily reference and color parts
        equation = MathTex(
            "6CO_2", "+", "6H_2O",  # Reactants
            r"\xrightarrow{\text{Light Energy}}",  # Arrow with label
            "C_6H_{12}O_6", "+", "6O_2",  # Products
            font_size=64
        ).center()

        # Isolate parts for coloring and animation
        reactants_tex = VGroup(equation.get_part_by_tex("6CO_2"), equation.get_part_by_tex("6H_2O"))
        products_tex = VGroup(equation.get_part_by_tex("C_6H_{12}O_6"), equation.get_part_by_tex("6O_2"))
        
        reactants_tex.set_color(BLUE_C)
        products_tex.set_color(TEAL_C)

        # Group parts for sequential animation
        reactants_anim_group = VGroup(equation[0], equation[1], equation[2])
        arrow_anim_group = equation[3]
        products_anim_group = VGroup(equation[4], equation[5], equation[6])
        
        # Animate reactants appearing
        self.play(FadeIn(reactants_anim_group, shift=UP * 0.3, run_time=1.0))
        self.wait(0.3)

        # Animate the reaction arrow
        self.play(FadeIn(arrow_anim_group, shift=UP * 0.3, run_time=1.0))
        self.wait(0.3)

        # Animate products appearing
        self.play(FadeIn(products_anim_group, shift=UP * 0.3, run_time=1.0))
        self.wait(0.5)

        # 3. EMPHASIS: Highlight key products
        glucose = equation.get_part_by_tex("C_6H_{12}O_6")
        oxygen = equation.get_part_by_tex("6O_2")

        # Highlight glucose ("their food")
        self.play(Indicate(glucose, color=YELLOW, scale_factor=1.1, run_time=1.2))
        self.wait(0.3)

        # Highlight oxygen ("the oxygen we breathe")
        self.play(Indicate(oxygen, color=YELLOW, scale_factor=1.1, run_time=1.2))
        self.wait(0.5)

        # 4. CLOSING: Fade out all elements
        self.play(
            *[FadeOut(mob) for mob in self.mobjects if mob is not None],
            run_time=0.6
        )
        self.wait(0.5)