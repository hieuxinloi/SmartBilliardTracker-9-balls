
import numpy as np

class GeometryUtils:
    @staticmethod
    def compute_iou(det1, det2):
        dist = np.sqrt((det1["x"] - det2["x"]) ** 2 + (det1["y"] - det2["y"]) ** 2)
 
        r1, r2 = det1["r"], det2["r"]
        
        if dist >= r1 + r2:
            intersection = 0.0
        elif dist <= abs(r1 - r2):
            intersection = np.pi * min(r1, r2) ** 2
        else:
            d = dist
            r1_sq, r2_sq = r1 ** 2, r2 ** 2
            
            cos_theta1 = (d * d + r1_sq - r2_sq) / (2 * d * r1)
            cos_theta2 = (d * d + r2_sq - r1_sq) / (2 * d * r2)
            
            theta1 = np.arccos(np.clip(cos_theta1, -1.0, 1.0))
            theta2 = np.arccos(np.clip(cos_theta2, -1.0, 1.0))
            
            sector1 = r1_sq * theta1
            sector2 = r2_sq * theta2
            
            triangle1 = 0.5 * r1_sq * np.sin(2 * theta1)
            triangle2 = 0.5 * r2_sq * np.sin(2 * theta2)
            
    
            intersection = sector1 + sector2 - triangle1 - triangle2
        
        union = np.pi * r1 ** 2 + np.pi * r2 ** 2 - intersection
        
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def compute_center(bbox):
        x1, y1, x2, y2 = bbox
        return (x1 + x2) / 2, (y1 + y2) / 2

    @staticmethod
    def compute_distance(p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))




def merge_overlapping_detections(detections, iou_threshold=0.7):

    if len(detections) <= 1:
        return detections
    
    sorted_dets = sorted(detections, key=lambda d: d["conf"], reverse=True)
    
    kept = []
    while sorted_dets:
        current = sorted_dets.pop(0)
        kept.append(current)
        
        sorted_dets = [det for det in sorted_dets if GeometryUtils.compute_iou(current, det) < iou_threshold]
    
    return kept
