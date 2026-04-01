from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Set up the initial reactants on screen from a previous state
        reactants = MathTex("6CO_2", "+", "6H_2O", color=WHITE).scale(1.2)
        
        # Define the products and the reaction arrow
        arrow = MathTex("\\rightarrow", color=WHITE).scale(1.2)
        glucose = MathTex("C_6H_{12}O_6", color=YELLOW_A).scale(1.2)
        plus_sign_product = MathTex("+", color=WHITE).scale(1.2)
        oxygen = MathTex("6O_2", color=BLUE_C).scale(1.2)

        # Group the full equation and arrange it to be centered on the screen
        full_equation = VGroup(
            reactants, arrow, glucose, plus_sign_product, oxygen
        ).arrange(RIGHT, buff=0.4).center()
        
        # Add reactants to the scene at the start, as if they were already there
        self.add(reactants)
        self.wait(0.5)

        # Animate the appearance of the arrow, fulfilling the first animation step
        # Narration: "...and boom! They transform them..."
        self.play(Create(arrow), run_time=1.0)

        # Animate the appearance of the glucose molecule
        # Narration: "...into one molecule of glucose – that's plant food..."
        self.play(Write(glucose), run_time=1.5)
        
        # Animate the appearance of the plus sign and oxygen
        # Narration: "...and six molecules of oxygen that WE breathe!"
        self.play(
            Write(plus_sign_product),
            Write(oxygen),
            run_time=1.5
        )
        
        # Create and animate text labels for the products
        glucose_text = Tex("Glucose", color=YELLOW_A).scale(0.9).to_edge(UP)
        oxygen_text = Tex("Oxygen", color=BLUE_C).scale(0.9).next_to(glucose_text, DOWN, buff=0.5)
        
        self.play(
            FadeIn(glucose_text, shift=DOWN),
            FadeIn(oxygen_text, shift=DOWN),
            run_time=1.0
        )

        # Create a visual flourish of oxygen molecules floating away
        o2_molecules = VGroup()
        for _ in range(6):
            o_atom1 = Dot(color=BLUE_C, radius=0.05)
            o_atom2 = Dot(color=BLUE_C, radius=0.05).next_to(o_atom1, RIGHT, buff=0.1)
            bond = Line(o_atom1.get_center(), o_atom2.get_center(), stroke_width=2, color=BLUE_C)
            molecule = VGroup(o_atom1, o_atom2, bond)
            molecule.move_to(oxygen.get_center() + np.random.uniform(-0.5, 0.5, 3))
            o2_molecules.add(molecule)

        # Fulfill the 1.5s wait while animating the oxygen molecules floating away
        self.play(
            LaggedStart(
                *[
                    m.animate.shift(UP * 2 + RIGHT * np.random.uniform(-1, 1)).fade(1)
                    for m in o2_molecules
                ],
                lag_ratio=0.15,
                run_time=1.5
            )
        )
        
        # Fade out the text labels
        # Narration: "It's pure natural magic!"
        self.play(
            FadeOut(glucose_text, shift=UP),
            FadeOut(oxygen_text, shift=UP),
            run_time=1.0
        )

        # Final wait to hold the completed equation on screen
        self.wait(1)