from manim import *

class Segment3Scene(Scene):
    """
    An animation showing the step-by-step construction of the balanced
    chemical equation for photosynthesis, following the 3Blue1Brown style guide.
    """
    def construct(self):
        # Define shared properties for all equations
        eq_font_size = 66
        
        # Define the sequence of equations to be animated.
        # Each is centered to ensure smooth transformations in the middle of the screen.
        
        # 1. Initial reactants: Carbon Dioxide and Water
        eq1 = MathTex(
            "CO_2 + H_2O",
            font_size=eq_font_size,
            color=WHITE
        ).center()
        
        # 2. Balanced reactants
        eq2 = MathTex(
            "6CO_2 + 6H_2O",
            font_size=eq_font_size,
            color=WHITE
        ).center()
        
        # 3. Reactants with energy input arrow
        eq3 = MathTex(
            "6CO_2 + 6H_2O \\xrightarrow{\\text{light energy}}",
            font_size=eq_font_size,
            color=WHITE
        ).center()
        
        # 4. Full balanced equation with products
        eq4 = MathTex(
            "6CO_2 + 6H_2O \\xrightarrow{\\text{light energy}} C_6H_{12}O_6 + 6O_2",
            font_size=eq_font_size,
            color=WHITE
        ).center()
        
        # Highlight the products (results/key terms) in YELLOW as per the style guide.
        eq4.set_color_by_tex("C_6H_{12}O_6 + 6O_2", YELLOW)

        # --- ANIMATION CHOREOGRAPHY ---
        # Total duration: 1.0 + 1.5 + 1.5 + 1.5 + 2.0 = 7.5 seconds

        # Step 1: Introduce the initial, unbalanced reactants.
        self.play(
            FadeIn(eq1, shift=DOWN * 0.3, run_time=1.0)
        )

        # Step 2: Morph to the balanced equation for the reactants.
        self.play(
            ReplacementTransform(eq1, eq2, run_time=1.5)
        )

        # Step 3: Add the reaction arrow indicating the need for light energy.
        self.play(
            ReplacementTransform(eq2, eq3, run_time=1.5)
        )

        # Step 4: Complete the equation by revealing the products, glucose and oxygen.
        self.play(
            ReplacementTransform(eq3, eq4, run_time=1.5)
        )

        # Step 5: Hold the final, complete equation for the viewer to read.
        self.wait(2.0)