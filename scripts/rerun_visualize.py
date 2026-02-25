"""
This script loads motion data from CSV files (in LAFAN format) and visualizes
the robot motion in 3D using Rerun. 

Usage:
    # Visualize a single CSV file
    uv run scripts/rerun_visualize.py --file_name data/fight1_subject2.csv
"""

import argparse
import time
from pathlib import Path
import numpy as np
import pinocchio as pin
import rerun as rr
import trimesh
import datetime

class RerunURDF():
    def __init__(self):
        self.name = 'g1'
        self.robot = pin.RobotWrapper.BuildFromURDF(
            'robots/g1_ufb/g1_29dof_rev_1_0.urdf', 
            'robots/g1_ufb', 
            pin.JointModelFreeFlyer()
        )
        self.Tpose = np.array([0,0,0.785,0,0,0,1,
                               -0.15,0,0,0.3,-0.15,0,
                               -0.15,0,0,0.3,-0.15,0,
                               0,0,0,
                               0, 1.57,0,1.57,0,0,0,
                               0,-1.57,0,1.57,0,0,0]).astype(np.float32)
        
        self.link2mesh = self.get_link2mesh()
        self.load_visual_mesh()
        self.update()
    
    def get_link2mesh(self):
        link2mesh = {}
        for visual in self.robot.visual_model.geometryObjects:
            mesh = trimesh.load_mesh(visual.meshPath)
            name = visual.name[:-2]
            mesh.visual = trimesh.visual.ColorVisuals()
            mesh.visual.vertex_colors = visual.meshColor
            link2mesh[name] = mesh
        return link2mesh
   
    def load_visual_mesh(self):       
        self.robot.framesForwardKinematics(pin.neutral(self.robot.model))
        for visual in self.robot.visual_model.geometryObjects:
            frame_name = visual.name[:-2]
            mesh = self.link2mesh[frame_name]
            
            frame_id = self.robot.model.getFrameId(frame_name)
            parent_joint_id = self.robot.model.frames[frame_id].parentJoint
            parent_joint_name = self.robot.model.names[parent_joint_id]
            frame_tf = self.robot.data.oMf[frame_id]
            joint_tf = self.robot.data.oMi[parent_joint_id]
            rr.log(f'urdf_{self.name}/{parent_joint_name}',
                   rr.Transform3D(translation=joint_tf.translation,
                                  mat3x3=joint_tf.rotation))
            
            relative_tf = joint_tf.inverse() * frame_tf
            mesh.apply_transform(relative_tf.homogeneous)
            rr.log(f'urdf_{self.name}/{parent_joint_name}/{frame_name}',
                   rr.Mesh3D(
                       vertex_positions=mesh.vertices,
                       triangle_indices=mesh.faces,
                       vertex_normals=mesh.vertex_normals,
                       vertex_colors=mesh.visual.vertex_colors,
                       albedo_texture=None,
                       vertex_texcoords=None,
                   ),
                   static=True)
    
    def update(self, configuration = None):
        self.robot.framesForwardKinematics(self.Tpose if configuration is None else configuration)
        for visual in self.robot.visual_model.geometryObjects:
            frame_name = visual.name[:-2]
            frame_id = self.robot.model.getFrameId(frame_name)
            parent_joint_id = self.robot.model.frames[frame_id].parentJoint
            parent_joint_name = self.robot.model.names[parent_joint_id]
            joint_tf = self.robot.data.oMi[parent_joint_id]
            rr.log(f'urdf_{self.name}/{parent_joint_name}',
                   rr.Transform3D(translation=joint_tf.translation,
                                  mat3x3=joint_tf.rotation))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_name', type=str, help="Path to CSV file", required=True)
    args = parser.parse_args()

    # Use CSV filename (without path) as part of the app name for separate windows
    csv_filename = Path(args.file_name).name
    rr.init(f'Reviz_{csv_filename}', spawn=True)
    rr.log('', rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)

    data = np.genfromtxt(args.file_name, delimiter=',')

    rerun_urdf = RerunURDF()
    for frame_nr in range(data.shape[0]):
        rr.set_time('frame_nr', sequence=frame_nr)
        configuration = data[frame_nr, :]
        rerun_urdf.update(configuration)
        time.sleep(0.03)