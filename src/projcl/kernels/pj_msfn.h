#ifndef PJ_MSFN_H__
#define PJ_MSFN_H__

/* determine constant small m */
double
pj_msfn(double sinphi, double cosphi, double es) {
	return (cosphi / sqrt (1. - es * sinphi * sinphi));
}

#endif /* PJ_MSFN_H__ */
