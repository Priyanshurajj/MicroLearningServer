from manim import *
import random

class Segment3Scene(Scene):
    def construct(self):
        # CONFIG
        # Target duration: ~6.0s
        # Colors from spec
        leaf_color = GREEN_E
        roots_color = MAROON_C
        co2_c_color = GRAY
        co2_o_color = RED
        h2o_o_color = BLUE
        h2o_h_color = WHITE
        label_color = WHITE
        bond_color = DARK_GRAY

        # 1. Create leaf and root diagrams
        leaf_diagram = Ellipse(width=4.5, height=2.2, color=leaf_color, fill_opacity=0.8)
        leaf_diagram.rotate(PI / 12).shift(UP * 0.7)
        
        root_start = leaf_diagram.get_bottom() + DOWN * 0.1
        roots_diagram = VGroup()
        main_root = Line(root_start, root_start + DOWN * 2, color=roots_color, stroke_width=6)
        roots_diagram.add(main_root)
        for i in range(1, 4):
            branch_start = main_root.point_from_proportion(i/3.5)
            roots_diagram.add(Line(branch_start, branch_start + LEFT * 0.5 + DOWN * 0.5, color=roots_color, stroke_width=4))
            roots_diagram.add(Line(branch_start, branch_start + RIGHT * 0.5 + DOWN * 0.5, color=roots_color, stroke_width=4))

        # 2. Define molecule creation functions
        def create_co2_molecule():
            carbon = Dot(color=co2_c_color, radius=0.1)
            oxygen1 = Dot(color=co2_o_color, radius=0.08).next_to(carbon, LEFT, buff=0.1)
            oxygen2 = Dot(color=co2_o_color, radius=0.08).next_to(carbon, RIGHT, buff=0.1)
            bond1 = Line(carbon.get_center(), oxygen1.get_center(), stroke_width=3, color=bond_color)
            bond2 = Line(carbon.get_center(), oxygen2.get_center(), stroke_width=3, color=bond_color)
            return VGroup(bond1, bond2, carbon, oxygen1, oxygen2).scale(0.8)

        def create_h2o_molecule():
            oxygen = Dot(color=h2o_o_color, radius=0.1)
            h_vect1 = rotate_vector(DOWN, -PI/4)
            h_vect2 = rotate_vector(DOWN, PI/4)
            hydrogen1 = Dot(color=h2o_h_color, radius=0.05).move_to(oxygen.get_center() + h_vect1 * 0.2)
            hydrogen2 = Dot(color=h2o_h_color, radius=0.05).move_to(oxygen.get_center() + h_vect2 * 0.2)
            bond1 = Line(oxygen.get_center(), hydrogen1.get_center(), stroke_width=3, color=bond_color)
            bond2 = Line(oxygen.get_center(), hydrogen2.get_center(), stroke_width=3, color=bond_color)
            return VGroup(bond1, bond2, oxygen, hydrogen1, hydrogen2).scale(0.8)

        # 3. Create labels
        co2_label = MathTex("CO_2", color=label_color).scale(1.2)
        co2_label.next_to(leaf_diagram, UP, buff=0.8).shift(LEFT * 3)

        h2o_label = MathTex("H_2O", color=label_color).scale(1.2)
        h2o_label.next_to(roots_diagram, DOWN, buff=0.5).shift(RIGHT * 2.5)

        # ANIMATION
        self.play(Create(leaf_diagram), Create(roots_diagram), run_time=1.5)
        self.wait(0.2)

        num_molecules = 5
        co2_start_pos = UP * 3.5 + LEFT * 2
        h2o_start_pos = DOWN * 3.5 + RIGHT * 1.5

        co2_molecules = VGroup(*[create_co2_molecule() for _ in range(num_molecules)])
        co2_molecules.arrange(buff=0.7).move_to(co2_start_pos)
        
        h2o_molecules = VGroup(*[create_h2o_molecule() for _ in range(num_molecules)])
        h2o_molecules.arrange(buff=0.7).move_to(h2o_start_pos)

        co2_anims = LaggedStart(
            *[m.animate.move_to(leaf_diagram.get_center() + 
                                 UP*random.uniform(-0.3, 0.3) + 
                                 RIGHT*random.uniform(-1, 1)) 
              for m in co2_molecules],
            lag_ratio=0.25
        )
        
        h2o_anims = LaggedStart(
            *[m.animate.move_to(roots_diagram.get_center() + 
                                 UP*random.uniform(-0.5, 0.5) + 
                                 LEFT*random.uniform(-1, 1)) 
              for m in h2o_molecules],
            lag_ratio=0.25
        )

        self.add(co2_molecules, h2o_molecules)
        
        self.play(
            AnimationGroup(
                co2_anims,
                h2o_anims,
                FadeIn(co2_label, shift=UP*0.5),
                FadeIn(h2o_label, shift=DOWN*0.5),
                lag_ratio=0.1
            ),
            run_time=3.0
        )
        
        self.play(
            FadeOut(co2_molecules),
            FadeOut(h2o_molecules),
            run_time=0.5
        )

        self.wait(1)