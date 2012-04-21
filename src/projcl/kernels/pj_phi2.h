/* determine latitude angle phi-2 */
#ifndef PJ_PHI2_H__
#define PJ_PHI2_H__

#include "constants.h"

#define PJ_PHI2_TOL 1.0e-8
#define PJ_PHI2_N_ITER 15

float
pj_phi2(float ts, float e, int* err) {
	float eccnth, Phi, con, dphi;
	int i;

	eccnth = .5f * e;
	Phi = HALFPI - 2.f * atan (ts);
	i = PJ_PHI2_N_ITER;
	do {
		con = e * sin (Phi);
		dphi = HALFPI - 2.f * atan (ts * pow((1.f - con) /
		   (1.f + con), eccnth)) - Phi;
		Phi += dphi;
	} while ( fabs(dphi) > PJ_PHI2_TOL && --i);
	if (i <= 0)
            *err = -18;
	return Phi;
}

#endif /* PJ_PHI2_H__ */

