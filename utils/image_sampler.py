import cv2
import os
import numpy as np

from datetime import datetime
from multiprocessing import Process, Queue
from multiprocessing.queues import Empty
from utils.log_manager import LogManager


class ImageRecorder:
    def __init__(self, save_directory, mode='whole', max_queue=200, new_process_threshold=90, max_processes=4):
        self.save_directory = save_directory
        self.mode = mode
        self.queue = Queue(maxsize=max_queue)
        self.new_process_threshold = new_process_threshold
        self.max_processes = max_processes
        self.processes = []
        self.running = True
        self.logger = LogManager.get_logger(__name__)

        self.start_new_process()

    def start_new_process(self):
        if len(self.processes) < self.max_processes:
            p = Process(target=self.save_images)
            p.start()
            self.processes.append(p)
            self.logger.info(f"[INFO] Started new process, total processes: {len(self.processes)}")
        else:
            self.logger.warning("[INFO] Maximum number of processes reached.")

    def save_images(self):
        while self.running or not self.queue.empty():
            try:
                frame, frame_id, boxes, centres = self.queue.get(timeout=3)

            except Empty:
                if not self.running:
                    break
                continue

            except KeyboardInterrupt:
                self.logger.info("[INFO] KeyboardInterrupt received in save_images. Exiting.")
                break

            # Process and save images based on mode
            self.process_frame(frame, frame_id, boxes, centres)

    def process_frame(self, frame, frame_id, boxes, centres):
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H%M%S.%f')[:-3] + 'Z'
        if self.mode == 'whole':
            self.save_frame(frame, frame_id, timestamp)
        elif self.mode == 'bbox':
            self.save_bboxes(frame, frame_id, boxes, timestamp)
        elif self.mode == 'square':
            self.save_squares(frame, frame_id, centres, timestamp)

    def save_frame(self, frame, frame_id, timestamp):
        filename = f"{timestamp}_frame_{frame_id}.png"
        filepath = os.path.join(self.save_directory, filename)
        cv2.imwrite(filepath, frame)

    def save_bboxes(self, frame, frame_id, boxes, timestamp):
        for contour_id, box in enumerate(boxes):
            startX, startY, width, height = box
            cropped_image = frame[startY:startY+height, startX:startX+width]
            filename = f"{timestamp}_frame_{frame_id}_n_{str(contour_id)}.png"
            filepath = os.path.join(self.save_directory, filename)
            cv2.imwrite(filepath, cropped_image)

    def save_squares(self, frame, frame_id, centres, timestamp):
        side_length = min(200, frame.shape[0])
        halfLength = side_length // 2
        for contour_id, centre in enumerate(centres):
            startX = max(centre[0] - np.random.randint(10, halfLength), 0)
            startY = max(centre[1] - np.random.randint(10, halfLength), 0)
            endX = startX + side_length
            endY = startY + side_length
            if endX > frame.shape[1]:
                startX = frame.shape[1] - side_length
            if endY > frame.shape[0]:
                startY = frame.shape[0] - side_length
            square_image = frame[startY:endY, startX:endX]
            filename = f"{timestamp}_frame_{frame_id}_n_{str(contour_id)}.png"
            filepath = os.path.join(self.save_directory, filename)
            cv2.imwrite(filepath, square_image)

    def add_frame(self, frame, frame_id, boxes, centres):
        if not self.queue.full():
            self.queue.put((frame, frame_id, boxes, centres))
        else:
            self.logger.info("[INFO] Queue is full, spinning up new process. Frame skipped.")

        if self.queue.qsize() > self.new_process_threshold and len(self.processes) < self.max_processes:
            self.start_new_process()

    def stop(self):
        """Stop image recording processes and clean up resources."""
        self.running = False

        try:
            while not self.queue.empty():
                self.queue.get_nowait()
        except Exception as e:
            self.logger.warning(f"Failed to clear queue: {e}")

        self.queue.close()
        self.queue.join_thread()

        for p in self.processes:
            try:
                p.join(timeout=1)
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=0.5)
            except Exception as e:
                self.logger.error(f"Failed to stop process: {e}")

        self.processes.clear()
        self.logger.info("[INFO] ImageRecorder stopped.")

    def terminate(self):
        """Force terminate all image recording processes."""
        self.running = False
        for p in self.processes:
            if p.is_alive():
                try:
                    p.terminate()
                    p.join(timeout=0.5)
                except Exception as e:
                    self.logger.error(f"Failed to terminate process: {e}")

        self.processes.clear()
        self.queue.close()
        self.queue.join_thread()
        self.logger.info("[INFO] All recording processes terminated forcefully.")