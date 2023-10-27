import sys
import numpy as np
import cv2
from openni import openni2, nite2, utils
import argparse

GRAY_COLOR = (64, 64, 64)
CAPTURE_SIZE_KINECT = (640, 480)
CAPTURE_SIZE_OTHERS = (640, 480)


def parse_arg():
    parser = argparse.ArgumentParser(description="Test OpenNI2 and NiTE2.")
    parser.add_argument("-w", "--window_width", type=int, default=1024, help="Specify the window width.")
    return parser.parse_args()


def draw_limb(img, ut, j1, j2, col):
    (x1, y1) = ut.convert_joint_coordinates_to_depth(j1.position.x, j1.position.y, j1.position.z)
    (x2, y2) = ut.convert_joint_coordinates_to_depth(j2.position.x, j2.position.y, j2.position.z)

    if 0.4 < j1.positionConfidence and 0.4 < j2.positionConfidence:
        c = GRAY_COLOR if (j1.positionConfidence < 1.0 or j2.positionConfidence < 1.0) else col
        cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), c, 1)

        c = GRAY_COLOR if (j1.positionConfidence < 1.0) else col
        cv2.circle(img, (int(x1), int(y1)), 2, c, -1)

        c = GRAY_COLOR if (j2.positionConfidence < 1.0) else col
        cv2.circle(img, (int(x2), int(y2)), 2, c, -1)


def draw_skeleton(img, ut, user, col):
    for idx1, idx2 in [
        (nite2.JointType.NITE_JOINT_HEAD, nite2.JointType.NITE_JOINT_NECK),
        # Upper Body
        (nite2.JointType.NITE_JOINT_NECK, nite2.JointType.NITE_JOINT_LEFT_SHOULDER),
        (nite2.JointType.NITE_JOINT_LEFT_SHOULDER, nite2.JointType.NITE_JOINT_TORSO),
        (nite2.JointType.NITE_JOINT_TORSO, nite2.JointType.NITE_JOINT_RIGHT_SHOULDER),
        (nite2.JointType.NITE_JOINT_RIGHT_SHOULDER, nite2.JointType.NITE_JOINT_NECK),
        # Left Hand
        (nite2.JointType.NITE_JOINT_LEFT_HAND, nite2.JointType.NITE_JOINT_LEFT_ELBOW),
        (nite2.JointType.NITE_JOINT_LEFT_ELBOW, nite2.JointType.NITE_JOINT_LEFT_SHOULDER),
        # Right Hand
        (nite2.JointType.NITE_JOINT_RIGHT_HAND, nite2.JointType.NITE_JOINT_RIGHT_ELBOW),
        (nite2.JointType.NITE_JOINT_RIGHT_ELBOW, nite2.JointType.NITE_JOINT_RIGHT_SHOULDER),
        # Lower Body
        (nite2.JointType.NITE_JOINT_TORSO, nite2.JointType.NITE_JOINT_LEFT_HIP),
        (nite2.JointType.NITE_JOINT_LEFT_HIP, nite2.JointType.NITE_JOINT_RIGHT_HIP),
        (nite2.JointType.NITE_JOINT_RIGHT_HIP, nite2.JointType.NITE_JOINT_TORSO),
        # Left Leg
        (nite2.JointType.NITE_JOINT_LEFT_FOOT, nite2.JointType.NITE_JOINT_LEFT_KNEE),
        (nite2.JointType.NITE_JOINT_LEFT_KNEE, nite2.JointType.NITE_JOINT_LEFT_HIP),
        # Right Leg
        (nite2.JointType.NITE_JOINT_RIGHT_FOOT, nite2.JointType.NITE_JOINT_RIGHT_KNEE),
        (nite2.JointType.NITE_JOINT_RIGHT_KNEE, nite2.JointType.NITE_JOINT_RIGHT_HIP),
    ]:
        draw_limb(img, ut, user.skeleton.joints[idx1], user.skeleton.joints[idx2], col)


def init_capture_device():
    openni2.initialize()
    nite2.initialize()
    return openni2.Device.open_any()


def close_capture_device():
    nite2.unload()
    openni2.unload()


def capture_skeleton():
    args = parse_arg()
    dev = init_capture_device()

    depth_stream = dev.create_depth_stream()
    depth_stream.start()

    dev_name = dev.get_device_info().name.decode("UTF-8")
    print("Device Name: {}".format(dev_name))
    use_kinect = False
    if dev_name == "Kinect":
        use_kinect = True
        print("Using Kinect.")

    try:
        user_tracker = nite2.UserTracker(dev)
    except utils.NiteError:
        print(
            "Unable to start the NiTE human tracker. Check "
            "the error messages in the console. Model data "
            "(s.dat, h.dat...) might be inaccessible."
        )
        sys.exit(-1)

    (img_w, img_h) = CAPTURE_SIZE_KINECT if use_kinect else CAPTURE_SIZE_OTHERS
    win_w = args.window_width
    win_h = int(img_h * win_w / img_w)

    while True:
        ut_frame = user_tracker.read_frame()

        depth_frame = depth_stream.read_frame()
        depth_frame_data = depth_frame.get_buffer_as_uint16()
        img = np.ndarray((depth_frame.height, depth_frame.width), dtype=np.uint16, buffer=depth_frame_data).astype(
            np.float32
        )
        if use_kinect:
            img = img[0:img_h, 0:img_w]

        (min_val, max_val, min_loc, max_loc) = cv2.minMaxLoc(img)
        if min_val < max_val:
            img = (img - min_val) / (max_val - min_val)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        if ut_frame.users:
            for user in ut_frame.users:
                if user.is_new():
                    print("New person id:{} detected.".format(user.id))
                    user_tracker.start_skeleton_tracking(user.id)
                elif (
                    user.state == nite2.UserState.NITE_USER_STATE_VISIBLE
                    and user.skeleton.state == nite2.SkeletonState.NITE_SKELETON_TRACKED
                ):
                    draw_skeleton(img, user_tracker, user, (255, 255, 255))

        cv2.imshow("Depth", cv2.resize(img, (win_w, win_h)))
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    close_capture_device()


if __name__ == "__main__":
    capture_skeleton()
