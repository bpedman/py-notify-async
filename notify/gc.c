/*--------------------------------------------------------------------*\
 * This file is part of Py-notify.                                    *
 *                                                                    *
 * Copyright (C) 2007, 2008 Paul Pogonyshev.                          *
 *                                                                    *
 * This library is free software; you can redistribute it and/or      *
 * modify it under the terms of the GNU Lesser General Public License *
 * as published by the Free Software Foundation; either version 2.1   *
 * of the License, or (at your option) any later version.             *
 *                                                                    *
 * This library is distributed in the hope that it will be useful,    *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of     *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  *
 * Lesser General Public License for more details.                    *
 *                                                                    *
 * You should have received a copy of the GNU Lesser General Public   *
 * License along with this library; if not, write to the Free         *
 * Software Foundation, Inc., 51 Franklin Street, Fifth Floor,        *
 * Boston, MA 02110-1301 USA                                          *
\*--------------------------------------------------------------------*/


#include <Python.h>


/* See Python documentation for why it prevents rare and very obscure bug.  Need to
 * backport for older Python versions.
 */
#ifdef Py_CLEAR
#  define Compatibility_CLEAR(object) Py_CLEAR (object)
#else
#  define Compatibility_CLEAR(object)                   \
      do                                                \
        {                                               \
          if (object)                                   \
            {                                           \
              PyObject *temp = (PyObject *) (object);   \
              (object) = NULL;                          \
              Py_DECREF (temp);                         \
            }                                           \
        }                                               \
      while (0)
#endif


/* Needed for Py3k, not defined earlier. */
#ifdef PyVarObject_HEAD_INIT
#  define Compatibility_VarObject_HEAD_INIT(ob_size) PyVarObject_HEAD_INIT (0, ob_size)
#else
#  define Compatibility_VarObject_HEAD_INIT(ob_size) PyObject_HEAD_INIT (0) ob_size,
#endif


/* Type fixup is not really needed for Py3k, but we do this anyway to keep difference with
 * 2.x version smaller.
 */
#if defined (PY_MAJOR_VERSION) && PY_MAJOR_VERSION >= 3
#  define Compatibility_Fix_TypeType(type, meta_type) type.ob_base.ob_base.ob_type = &meta_type;
#else
#  define Compatibility_Fix_TypeType(type, meta_type) type.ob_type = &meta_type;
#endif


/* Again working around changes in Py3k. */
#ifdef PyMODINIT_FUNC
#  define Compatibility_MODINIT_FUNC PyMODINIT_FUNC
#else
#  ifdef DL_EXPORT
#    define Compatibility_MODINIT_FUNC DL_EXPORT (void)
#  else
#    define Compatibility_MODINIT_FUNC void
#  endif
#endif


/* Also compatibility, but let's avoid long name in this case. */
#if defined (PY_MAJOR_VERSION) && PY_MAJOR_VERSION >= 3
#  define PyInt_AsLong   PyLong_AsLong
#  define PyInt_FromLong PyLong_FromLong
#endif


/* Hide difference between old strings and Unicode strings used in Py3k. */
#if defined (PY_MAJOR_VERSION) && PY_MAJOR_VERSION >= 3
#  define Compatibility_String_FromString PyUnicode_FromString
#  define Compatibility_String_AsString   PyUnicode_AsString
#else
#  define Compatibility_String_FromString PyString_FromString
#  define Compatibility_String_AsString   PyString_AsString
#endif



/*- Type forward declarations --------------------------------------*/

typedef
struct
{
  PyObject_HEAD
  long int  num_active_protections;
}
FastGCProtector;


typedef
struct
{
  PyObject_HEAD
  PyObject *  protected_objects_dict;
  long int    num_active_protections;
}
RaisingGCProtector;


typedef  RaisingGCProtector  DebugGCProtector;



/*- Functions forward declarations ---------------------------------*/

static int          GCProtectorMeta_setattro        (PyObject *type,
                                                     PyObject *name, PyObject *value);
static PyObject *   GCProtectorMeta_get_default     (PyObject *type, void *context);
static int          GCProtectorMeta_set_default     (PyObject *type, PyObject *value,
                                                     void *context);

static void         AbstractGCProtector_dealloc     (PyObject *self);
static PyObject *   AbstractGCProtector_protect     (PyObject *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   AbstractGCProtector_unprotect   (PyObject *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   AbstractGCProtector_set_default (PyObject *null,
                                                     PyObject *arguments, PyObject *keywords);

static int          FastGCProtector_init            (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         FastGCProtector_dealloc         (FastGCProtector *self);
static PyObject *   FastGCProtector_protect         (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   FastGCProtector_unprotect       (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   FastGCProtector_get_num_active_protections
                      (FastGCProtector *self);

static int          RaisingGCProtector_init         (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         RaisingGCProtector_dealloc      (RaisingGCProtector *self);
static PyObject *   RaisingGCProtector_protect      (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   RaisingGCProtector_unprotect    (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   RaisingGCProtector_get_num_object_protections
                                                    (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   RaisingGCProtector_get_num_protected_objects
                      (RaisingGCProtector *self);
static PyObject *   RaisingGCProtector_get_num_active_protections
                      (RaisingGCProtector *self);

static PyObject *   DebugGCProtector_unprotect      (DebugGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);



/*- Documentation --------------------------------------------------*/

#define MODULE_DOC "\
A module for protecting objects from garbage collector.  Sometimes, objects that don't \
have a reference to them (and so are valid garbage collector targets) need to stay alive.  \
Good example of this are logic L{conditions <condition>}: their state can change because \
they have term conditions, yet they may be not referenced from anywhere, since handlers \
don't need a reference to notice a state change.\n\
\n\
This module defines both a simple L{interface <AbstractGCProtector>} and several \
implementations, some, which are suitable for production use (C{L{FastGCProtector}}), \
some for debugging purposes (C{L{RaisingGCProtector}}, C{L{DebugGCProtector}}.)\n\
\n\
Py-notify classes use value of the C{L{AbstractGCProtector.default}} variable as the \
protector instance.  In case you run into a problem, \
use C{L{AbstractGCProtector.set_default}} static method somewhere near your program beginning \
to set it to an instance of C{DebugGCProtector} or a similar class to track the problem down. \
However, we believe that Py-notify classes must not cause problems themselves, they may pop up \
only if you use a garbage-collection protector yourself."


#define UNPROTECTION_ERROR_DOC "\
Error that is raised by some L{garbage-collection protectors <AbstractGCProtector>} when you try \
to L{unprotect <AbstractGCProtector.unprotect>} an object more times than it had been \
L{protected <AbstractGCProtector.protect>}.  Of the standard protectors only \
C{L{RaisingGCProtector}} ever raises these exceptions."


#define GC_PROTECTOR_META_DOC "\
A meta-class for C{L{AbstractGCProtector}}.  Its only purpose is to define C{L{default}} \
property of the class.  In principle, it can be used for your classes too, but better subclass \
C{AbstractGCProtector} instead."

#define GC_PROTECTOR_META_DEFAULT_DOC "\
Current default GC protector.  Starts out as an instance of C{L{FastGCProtector}}, but can be \
changed for debugging purposes.  Note that setting this class property is only possible if \
current default protector doesn't have any active protections, i.e. if its \
C{num_active_protections} property is zero (or has any false truth value).  This is generally \
true only at the start of the program, so you cannot arbitrarily switch protectors.  Doing so \
would lead to unpredictable consequences, up to crashing the interpreter, therefore the \
restriction."


#define ABSTRACT_GC_PROTECTOR_DOC "\
Simple protector interface with two methods for implementations to define."

#define ABSTRACT_GC_PROTECTOR_PROTECT_DOC "\
protect(self, object) \
\n\
Protect C{object} from being garbage-collected.  It is legal to protect same C{object} \
several times and an object is prevented from being garbage-collected if it has been \
protected at least once.  As a special case, if C{object} is C{None}, this function does \
nothing.\n\
\n\
For convenience, this function always returns C{object} itself.\n\
\n\
@rtype: C{object}"

#define ABSTRACT_GC_PROTECTOR_UNPROTECT_DOC "\
unprotect(self, object) \
\n\
Unprotect C{object}.  If has been protected once only or exactly one time more than times it \
has been unprotected, make it a legal target for garbage collection again.  It is an error \
to call C{unprotect} more times than C{protect} for a same object, and descendant behaviour \
in this case is undefined.  It may even crash Python.  However, as a special case, if \
C{object} is C{None}, this function does nothing.  In particular, it is legal to `unprotect' \
C{None} without having protected it first, because it will be a no-op and not lead to bugs.\n\
\n\
\n\
For convenience, this function always returns C{object} itself.\n\
\n\
@rtype: C{object}"

#define ABSTRACT_GC_PROTECTOR_SET_DEFAULT_DOC "\
set_default(protector) \
\n\
This method is deprecated.  Instead, set C{AbstractGCProtector.default} directly."


#define FAST_GC_PROTECTOR_DOC "\
Default fast implementation of C{AbstractGCProtector} interface.  It is suitable for \
production use, but difficult to debug problems with, because it doesn't track what has and \
what has not be protected.  For that purpose, use C{L{RaisingGCProtector}} or \
C{L{DebugGCProtector}}."

#define FAST_GC_PROTECTOR_PROTECT_DOC                                   \
  NULL

#define FAST_GC_PROTECTOR_UNPROTECT_DOC                                 \
  NULL

#define FAST_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC "\
Number of protections currently in effect.  This number can be larger than the number of distinct \
protected objects.  Actually, since C{FastGCProtector} doesn't track protected objects, it cannot \
determine number of protected objects in principle.  Use C{L{RaisingGCProtector}} or a subclass \
if you need that information."


#define RAISING_GC_PROTECTOR_DOC "\
Implementation of C{AbstractGCProtector} interface suitable for aggressively debugging \
possible problems.  Instances of this class track what they have protected so far and how \
many times.  If you try to unprotect an object more times than it has been protected, an \
exception will be raised.\n\
\n\
There is also a number of functions and properties in this class that allow you to retrieve \
various protection information.\n\
\n\
@see: C{L{DebugGCProtector}}"

#define RAISING_GC_PROTECTOR_PROTECT_DOC                                \
  NULL

#define RAISING_GC_PROTECTOR_UNPROTECT_DOC                              \
  NULL

#define RAISING_GC_PROTECTOR_GET_NUM_OBJECT_PROTECTIONS "\
get_num_object_protections(self, object) \
\n\
Get the number of times given C{object} is protected, i.e. number of times it has to be \
L{unprotected <unprotect>} to become a legal target for garbage collection again."

#define RAISING_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC "\
Number of distinct objects currently protected.  I.e. number of times each particular object is \
protected is not relevant for this property.\n\
\n\
@see: C{L{num_active_protections}}"

#define RAISING_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC                 \
  NULL


#define DEBUG_GC_PROTECTOR_DOC "\
Implementation of C{AbstractGCProtector} interface suitable for debugging possible problems. \
Instances of this class track what they have protected so far and how many times.  If you try to \
unprotect an object more times than it has been protected, a stack trace will be printed and \
nothing will be done.  Note that unlike C{L{RaisingGCProtector}}, no exception will be thrown.\n\
\n\
There is also a number of functions and properties in this class that allow you to retrieve \
various protection information.\n\
\n\
@see: C{L{RaisingGCProtector}}"

#define DEBUG_GC_PROTECTOR_UNPROTECT_DOC                                \
  NULL



/*- Types ----------------------------------------------------------*/

PyGetSetDef  GCProtectorMeta_properties[]
  = { { "default", GCProtectorMeta_get_default, GCProtectorMeta_set_default,
        GC_PROTECTOR_META_DEFAULT_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

PyTypeObject  GCProtectorMeta_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify.gc.GCProtectorMeta",                   /* tp_name           */
      sizeof (PyHeapTypeObject),                     /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     0,                            /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      GCProtectorMeta_setattro,                      /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      GC_PROTECTOR_META_DOC,                         /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      0,                                             /* tp_methods        */
      0,                                             /* tp_members        */
      GCProtectorMeta_properties,                    /* tp_getset         */
      0,                                             /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       0,                            /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };


PyMethodDef  AbstractGCProtector_methods[]
  = { { "protect",     (PyCFunction) AbstractGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS,             ABSTRACT_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction) AbstractGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS,               ABSTRACT_GC_PROTECTOR_UNPROTECT_DOC },
      { "set_default", (PyCFunction) AbstractGCProtector_set_default,
        METH_VARARGS | METH_KEYWORDS | METH_STATIC, ABSTRACT_GC_PROTECTOR_SET_DEFAULT_DOC },
      { NULL, NULL, 0, NULL } };

PyTypeObject  AbstractGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify.gc.AbstractGCProtector",               /* tp_name           */
      sizeof (PyObject),                             /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     AbstractGCProtector_dealloc,  /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      ABSTRACT_GC_PROTECTOR_DOC,                     /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      AbstractGCProtector_methods,                   /* tp_methods        */
      0,                                             /* tp_members        */
      0,                                             /* tp_getset         */
      0,                                             /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       0,                            /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };


PyMethodDef  FastGCProtector_methods[]
  = { { "protect",     (PyCFunction) FastGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS, FAST_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction) FastGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, FAST_GC_PROTECTOR_UNPROTECT_DOC },
      { NULL, NULL, 0, NULL } };

PyGetSetDef  FastGCProtector_properties[]
  = { { "num_active_protections", (getter) FastGCProtector_get_num_active_protections, NULL,
        FAST_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

PyTypeObject  FastGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify.gc.FastGCProtector",                   /* tp_name           */
      sizeof (FastGCProtector),                      /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     FastGCProtector_dealloc,      /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      FAST_GC_PROTECTOR_DOC,                         /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      FastGCProtector_methods,                       /* tp_methods        */
      0,                                             /* tp_members        */
      FastGCProtector_properties,                    /* tp_getset         */
      (PyTypeObject *) &AbstractGCProtector_Type,    /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       FastGCProtector_init,         /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };


PyMethodDef  RaisingGCProtector_methods[]
  = { { "protect",     (PyCFunction) RaisingGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS, RAISING_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction) RaisingGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, RAISING_GC_PROTECTOR_UNPROTECT_DOC },
      { "get_num_object_protections", (PyCFunction) RaisingGCProtector_get_num_object_protections,
        METH_VARARGS | METH_KEYWORDS, RAISING_GC_PROTECTOR_GET_NUM_OBJECT_PROTECTIONS },
      { NULL, NULL, 0, NULL } };

PyGetSetDef  RaisingGCProtector_properties[]
  = { { "num_protected_objects", (getter) RaisingGCProtector_get_num_protected_objects, NULL,
        RAISING_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC, NULL },
      { "num_active_protections", (getter) RaisingGCProtector_get_num_active_protections, NULL,
        RAISING_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

PyTypeObject  RaisingGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify.gc.RaisingGCProtector",                /* tp_name           */
      sizeof (RaisingGCProtector),                   /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     RaisingGCProtector_dealloc,   /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      RAISING_GC_PROTECTOR_DOC,                      /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      RaisingGCProtector_methods,                    /* tp_methods        */
      0,                                             /* tp_members        */
      RaisingGCProtector_properties,                 /* tp_getset         */
      (PyTypeObject *) &AbstractGCProtector_Type,    /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       RaisingGCProtector_init,      /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };


PyMethodDef  DebugGCProtector_methods[]
  = { { "unprotect",   (PyCFunction) DebugGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, DEBUG_GC_PROTECTOR_UNPROTECT_DOC },
      { NULL, NULL, 0, NULL } };

PyTypeObject  DebugGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify.gc.DebugGCProtector_Type",             /* tp_name           */
      sizeof (DebugGCProtector),                     /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     0,                            /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      DEBUG_GC_PROTECTOR_DOC,                        /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      DebugGCProtector_methods,                      /* tp_methods        */
      0,                                             /* tp_members        */
      0,                                             /* tp_getset         */
      (PyTypeObject *) &RaisingGCProtector_Type,     /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       0,                            /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };



/*- Static variables -----------------------------------------------*/

static PyObject *  raise_not_implemented_exception = NULL;

static char *      no_keywords[]           = { NULL };
static char *      object_keywords[]       = { "object", NULL };

static PyObject *  unprotection_error_type = NULL;

static PyObject *  default_protector       = NULL;
static PyObject *  default_attribute_name  = NULL;



/*- GCProtectorMeta type methods -----------------------------------*/

static int
GCProtectorMeta_setattro (PyObject *type, PyObject *name, PyObject *value)
{
  switch (PyObject_RichCompareBool (name, default_attribute_name, Py_EQ))
    {
    case 1:
      return PyObject_GenericSetAttr (type, name, value);

    case 0:
      return PyType_Type.tp_setattro (type, name, value);

    default:
      return -1;
    }
}


static PyObject *
GCProtectorMeta_get_default (PyObject *type, void *context)
{
  Py_INCREF (default_protector);
  return default_protector;
}

static int
GCProtectorMeta_set_default (PyObject *type, PyObject *value, void *context)
{
  if (value == default_protector)
    return 0;

  switch (PyObject_IsInstance (value, (PyObject *) &AbstractGCProtector_Type))
    {
    case 1:
      {
        PyObject *num_active_protections = PyObject_GetAttrString (default_protector,
                                                                   "num_active_protections");

        if (num_active_protections)
          {
            switch (PyObject_IsTrue (num_active_protections))
              {
              case 0:
                Py_DECREF (num_active_protections);
                break;

              case 1:
                {
                  PyObject *as_string = PyObject_Str (num_active_protections);

                  if (as_string)
                    {
                      PyErr_Format (PyExc_ValueError,
                                    ("cannot set a different GC protector: current has active "
                                     "protections (num_active_protections = %.200s)"),
                                    Compatibility_String_AsString (as_string));
                    }
                  else
                    {
                      PyErr_Clear ();
                      PyErr_SetString (PyExc_ValueError, ("cannot set a different GC protector: "
                                                          "current has active protections"));
                    }
                }

              default:
                Py_DECREF (num_active_protections);
                return -1;
              }
          }
        else
          {
            /* Assume that there is no such attribute then. */
            PyErr_Clear ();
          }

        Py_DECREF (default_protector);

        default_protector = value;
        Py_INCREF (default_protector);

        return 0;
      }

    case 0:
      PyErr_Format (PyExc_ValueError,
                    ("can only set AbstractGCProtector.default to an instance of "
                     "AbstractGCProtector; got %.200s instead"),
                    value->ob_type->tp_name);
      break;
    }

  return -1;
}



/*- AbstractGCProtector type methods -------------------------------*/

static void
AbstractGCProtector_dealloc (PyObject *self)
{
  self->ob_type->tp_free (self);
}


static PyObject *
AbstractGCProtector_protect (PyObject *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.AbstractGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  return PyObject_CallFunction (raise_not_implemented_exception, "Os", self, "protect");
}


static PyObject *
AbstractGCProtector_unprotect (PyObject *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.AbstractGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  return PyObject_CallFunction (raise_not_implemented_exception, "Os", self, "unprotect");
}


/* Deprecated old function.  Assigning directly to `default' attribute is now possible and
 * is preferred.
 */
static PyObject *
AbstractGCProtector_set_default (PyObject *null, PyObject *arguments, PyObject *keywords)
{
  static char *  protector_keywords[] = { "protector", NULL };

  PyObject *new_protector;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O!:notify.gc.AbstractGCProtector.unprotect",
                                    protector_keywords, &AbstractGCProtector_Type, &new_protector))
    return NULL;

  if (GCProtectorMeta_set_default (NULL, new_protector, NULL) == -1)
    return NULL;

  Py_INCREF (Py_None);
  return Py_None;
}



/*- FastGCProtector type methods -----------------------------------*/

static PyObject *
FastGCProtector_new (void)
{
  return PyObject_CallFunctionObjArgs ((PyObject *) &FastGCProtector_Type, NULL);
}


static int
FastGCProtector_init (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":notify.gc.FastGCProtector",
                                    no_keywords))
    return -1;

  return 0;
}


static void
FastGCProtector_dealloc (FastGCProtector *self)
{
  ((PyObject *) self)->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
FastGCProtector_protect (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.FastGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      Py_INCREF (object);
      ++self->num_active_protections;
    }

  Py_INCREF (object);
  return object;
}


static PyObject *
FastGCProtector_unprotect (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.FastGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    --self->num_active_protections;
  else
    Py_INCREF (object);

  /* `object' reference counter is implicitly decremented by below return statement. */
  return object;
}


static PyObject *
FastGCProtector_get_num_active_protections (FastGCProtector *self)
{
  return PyInt_FromLong (self->num_active_protections);
}



/*- RaisingGCProtector type methods --------------------------------*/

static int
RaisingGCProtector_init (RaisingGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":notify.gc.RaisingGCProtector",
                                    no_keywords))
    return -1;

  Compatibility_CLEAR (self->protected_objects_dict);
  self->protected_objects_dict = PyDict_New ();

  if (!self->protected_objects_dict)
    return -1;

  return 0;
}


static void
RaisingGCProtector_dealloc (RaisingGCProtector *self)
{
  Compatibility_CLEAR (self->protected_objects_dict);
  ((PyObject *) self)->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
RaisingGCProtector_protect (RaisingGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.RaisingGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      PyObject *id;
      PyObject *num_protections;
      long int  num_protections_new;

      id = PyLong_FromVoidPtr (object);
      if (!id)
        return NULL;

      num_protections = PyDict_GetItem (self->protected_objects_dict, id);

      if (num_protections)
        num_protections_new = PyInt_AsLong (num_protections) + 1;
      else
        num_protections_new = 1;

      num_protections = PyInt_FromLong (num_protections_new);
      if (!num_protections)
        {
          Py_DECREF (id);
          return NULL;
        }

      PyDict_SetItem (self->protected_objects_dict, id, num_protections);
      Py_DECREF (num_protections);

      Py_DECREF (id);

      /* Do protect finally. */
      Py_INCREF (object);
      ++self->num_active_protections;
    }

  Py_INCREF (object);
  return object;
}


static PyObject *
RaisingGCProtector_unprotect (RaisingGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.RaisingGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      PyObject *id;
      PyObject *num_protections;

      id = PyLong_FromVoidPtr (object);
      if (!id)
        return NULL;

      num_protections = PyDict_GetItem (self->protected_objects_dict, id);

      if (num_protections)
        {
          long int  num_protections_new = PyInt_AsLong (num_protections) - 1;

          if (num_protections_new)
            {
              num_protections = PyInt_FromLong (num_protections_new);
              if (!num_protections)
                {
                  Py_DECREF (id);
                  return NULL;
                }

              PyDict_SetItem (self->protected_objects_dict, id, num_protections);
              Py_DECREF (num_protections);
            }
          else
            PyDict_DelItem (self->protected_objects_dict, id);

          Py_DECREF (id);
          --self->num_active_protections;
        }
      else
        {
          const char *type_name = ((PyObject *) self)->ob_type->tp_name;

          if (type_name)
            {
              type_name = strrchr (type_name, '.');

              if (type_name)
                type_name += 1;
              else
                type_name = ((PyObject *) self)->ob_type->tp_name;
            }
          else
            type_name = "?";

          PyErr_Format (unprotection_error_type,
                        "object is not protected by this %s", type_name);

          Py_DECREF (id);
          return NULL;
        }
    }
  else
    {
      /* So that the return statement at the end does no implicit unprotection. */
      Py_INCREF (object);
    }

  /* `object' reference counter is implicitly decremented by below return statement. */
  return object;
}


static PyObject *
RaisingGCProtector_get_num_object_protections (RaisingGCProtector *self,
                                               PyObject *arguments, PyObject *keywords)
{
  PyObject *object;
  PyObject *id;
  PyObject *num_protections;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.RaisingGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  id = PyLong_FromVoidPtr (object);
  if (!id)
    return NULL;

  num_protections = PyDict_GetItem (self->protected_objects_dict, id);

  if (num_protections)
    {
      Py_INCREF (num_protections);
      return num_protections;
    }
  else
    return PyInt_FromLong (0);
}


static PyObject *
RaisingGCProtector_get_num_protected_objects (RaisingGCProtector *self)
{
  return PyInt_FromLong (PyDict_Size (self->protected_objects_dict));
}


static PyObject *
RaisingGCProtector_get_num_active_protections (RaisingGCProtector *self)
{
  return PyInt_FromLong (self->num_active_protections);
}



/*- DebugGCProtector type methods ----------------------------------*/

static PyObject *
DebugGCProtector_unprotect (DebugGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  /* For a proper exception message and so we can assume that if super unprotect() method
   * fails, than it is because object is not protected, not because of wrong arguments.
   */
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.DebugGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  if (!RaisingGCProtector_unprotect (self, arguments, keywords))
    {
      PyErr_Print ();
      PyErr_Clear ();

      /* So that the return statement does no implicit unprotection. */
      Py_INCREF (object);
    }

  return object;
}



/*- Module initialization ------------------------------------------*/

#define REGISTER_TYPE(dictionary, type, meta_type, name, error_label)   \
  do                                                                    \
    {                                                                   \
      Compatibility_Fix_TypeType (type, meta_type);                     \
      type.tp_alloc = PyType_GenericAlloc;                              \
      type.tp_new   = PyType_GenericNew;                                \
      if (PyType_Ready (&type) == -1                                    \
          || (PyDict_SetItemString (dictionary, name,                   \
                                    (PyObject *) &type)                 \
              == -1))                                                   \
        goto error_label;                                               \
    }                                                                   \
  while (0)


Compatibility_MODINIT_FUNC
initgc (void)
{
  PyObject *module                        = NULL;
  PyObject *dictionary;
  PyObject *utilities                     = NULL;
  PyObject *unprotection_error_dictionary = NULL;

  module = Py_InitModule ("notify.gc", NULL);
  if (!module)
    goto error;

  dictionary = PyModule_GetDict (module);
  if (!dictionary)
    goto error;

  default_attribute_name = Compatibility_String_FromString ("default");
  if (!default_attribute_name)
    goto error;

  utilities = PyImport_ImportModule ("notify.utils");
  if (!utilities)
    goto error;

  raise_not_implemented_exception = PyDict_GetItemString (PyModule_GetDict (utilities),
                                                          "raise_not_implemented_exception");
  if (!raise_not_implemented_exception)
    {
      if (!PyErr_Occurred ())
        {
          PyErr_SetString (PyExc_ImportError,
                           ("notify.gc: cannot import "
                            "raise_not_implemented_exception from notify.utils"));
        }

      goto error;
    }

  Py_DECREF (utilities);

  unprotection_error_dictionary = Py_BuildValue ("{ss}", "__doc__", UNPROTECTION_ERROR_DOC);
  if (!unprotection_error_dictionary)
    goto error;

  unprotection_error_type = PyErr_NewException ("notify.gc.UnprotectionError",
                                                PyExc_ValueError, unprotection_error_dictionary);
  if (!unprotection_error_type)
    goto error;

  if (PyDict_SetItemString (dictionary, "UnprotectionError", unprotection_error_type) == -1)
    goto error;

  GCProtectorMeta_Type.tp_base = &PyType_Type;

  REGISTER_TYPE (dictionary, GCProtectorMeta_Type,     PyType_Type, "GCProtectorMeta",     error);
  REGISTER_TYPE (dictionary, AbstractGCProtector_Type, GCProtectorMeta_Type,
                 "AbstractGCProtector", error);

  REGISTER_TYPE (dictionary, FastGCProtector_Type,     PyType_Type, "FastGCProtector",     error);
  REGISTER_TYPE (dictionary, RaisingGCProtector_Type,  PyType_Type, "RaisingGCProtector",  error);
  REGISTER_TYPE (dictionary, DebugGCProtector_Type,    PyType_Type, "DebugGCProtector",    error);

  default_protector = FastGCProtector_new ();
  if (!default_protector)
    goto error;

  if (PyModule_AddStringConstant (module, "__doc__", MODULE_DOC) == -1)
    goto error;
  if (PyModule_AddStringConstant (module, "__docformat__", "epytext en") == -1)
    goto error;

  return;

 error:

  Py_XDECREF (module);
  Py_XDECREF (utilities);
  Py_XDECREF (unprotection_error_dictionary);
  Py_XDECREF (raise_not_implemented_exception);
  Py_XDECREF (unprotection_error_type);
  Py_XDECREF (default_protector);
}


/*
 * Local variables:
 * coding: utf-8
 * mode: c
 * c-basic-offset: 2
 * indent-tabs-mode: nil
 * fill-column: 90
 * End:
 */
