import rclpy
from rclpy.node import Node

from sensor_msgs.msg import NavSatFix

import serial
import pynmea2



class GPSNode(Node):

    def __init__(self):

        super().__init__('gps_node')


        # ==================================================
        # GPS Publisher
        # ==================================================

        self.publisher = self.create_publisher(

            NavSatFix,

            '/fix',

            10

        )



        # ==================================================
        # UART Configuration
        # ==================================================

        self.port = "/dev/ttyS4"

        self.baudrate = 9600



        try:

            self.gps = serial.Serial(

                self.port,

                self.baudrate,

                timeout=1

            )


            self.get_logger().info(

                "SAM-M8Q GPS connected on /dev/ttyS4"

            )


        except Exception as e:


            self.get_logger().error(

                f"GPS connection failed: {e}"

            )


            self.gps = None



        # ==================================================
        # Timer
        # ==================================================

        self.timer = self.create_timer(

            0.1,

            self.read_gps

        )



    def read_gps(self):


        if self.gps is None:

            return



        try:


            line = self.gps.readline().decode(

                "ascii",

                errors="replace"

            )



            if line.startswith("$GPGGA"):


                msg = pynmea2.parse(line)



                gps_msg = NavSatFix()



                gps_msg.header.stamp = (

                    self.get_clock()

                    .now()

                    .to_msg()

                )


                gps_msg.header.frame_id = "gps_link"



                # Latitude

                gps_msg.latitude = msg.latitude



                # Longitude

                gps_msg.longitude = msg.longitude



                # Altitude

                if msg.altitude:

                    gps_msg.altitude = float(

                        msg.altitude

                    )



                self.publisher.publish(

                    gps_msg

                )


        except Exception as e:


            self.get_logger().warning(

                f"GPS read error: {e}"

            )





def main(args=None):


    rclpy.init(args=args)


    node = GPSNode()


    rclpy.spin(node)


    node.destroy_node()


    rclpy.shutdown()




if __name__ == "__main__":

    main()
