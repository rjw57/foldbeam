#ifndef PJ_MSFN_H__
#define PJ_MSFN_H__

/* determine constant small m */
float
pj_msfn(float sinphi, float cosphi, float es) {
    return (cosphi / sqrt (1. - es * sinphi * sinphi));
}

#endif /* PJ_MSFN_H__ */
