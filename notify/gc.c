/*--------------------------------------------------------------------*\
 * This file is part of Py-notify.                                    *
 *                                                                    *
 * Copyright (C) 2007 Paul Pogonyshev.                                *
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


/*- Type forward declarations --------------------------------------*/

typedef
struct
{
  PyObject_HEAD
  long int  num_protected_objects;
}
FastGCProtector;


/*- Functions forward declarations ---------------------------------*/

static void         AbstractGCProtector_dealloc     (PyObject *self);
static PyObject *   AbstractGCProtector_protect     (PyObject *self, PyObject *arguments);
static PyObject *   AbstractGCProtector_unprotect   (PyObject *self, PyObject *arguments);
static PyObject *   AbstractGCProtector_set_default (PyObject *null, PyObject *arguments);

static int          FastGCProtector_init            (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         FastGCProtector_dealloc         (FastGCProtector *self);
static PyObject *   FastGCProtector_protect         (FastGCProtector *self, PyObject *arguments);
static PyObject *   FastGCProtector_unprotect       (FastGCProtector *self, PyObject *arguments);
static PyObject *   FastGCProtector_get_num_protected_objects
                      (FastGCProtector *self);


/*- Documentation --------------------------------------------------*/

#define MODULE_DOC "\
A module for protecting objects from garbage collector.  Sometimes, objects that don't \
have a reference to them (and so are valid garbage collector targets) need to stay alive.  \
Good example of this are logic L{conditions <condition>}: their state can change because \
they have term conditions, yet they may be not referenced from anywhere, since handlers \
don't need a reference to notice a state change.\n\
\n\
This module defines both a simple L{interface <AbstractGCProtector>} and several \
implementations, some which are suitable for production use (C{L{FastGCProtector}}), \
some for debugging purposes."


#define GC_PROTECTOR_DOC                                                \
  NULL

#define GC_PROTECTOR_PROTECT_DOC                                        \
  NULL

#define GC_PROTECTOR_UNPROTECT_DOC                                      \
  NULL

#define GC_PROTECTOR_SET_DEFAULT_DOC                                    \
  NULL


#define FAST_GC_PROTECTOR_DOC                                           \
  NULL

#define FAST_GC_PROTECTOR_PROTECT_DOC                                   \
  NULL

#define FAST_GC_PROTECTOR_UNPROTECT_DOC                                 \
  NULL

#define FAST_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC                     \
  NULL


/*- Types ----------------------------------------------------------*/

PyMethodDef  AbstractGCProtector_methods[]
  = { { "protect",     (PyCFunction)  AbstractGCProtector_protect,     METH_VARARGS,
        GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction)  AbstractGCProtector_unprotect,   METH_VARARGS,
        GC_PROTECTOR_UNPROTECT_DOC },
      { "set_default", (PyCFunction)  AbstractGCProtector_set_default, METH_VARARGS | METH_STATIC,
        GC_PROTECTOR_SET_DEFAULT_DOC },
      { NULL, NULL, 0, NULL } };

PyTypeObject  AbstractGCProtector_Type
  = { PyObject_HEAD_INIT (NULL)
      0,                                             /* ob_size           */
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
      GC_PROTECTOR_DOC,                              /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      AbstractGCProtector_methods,                   /* tp_methods        */
      0,                                             /* tp_members        */
      0,                                             /* tp_getset         */
      (PyTypeObject *) &PyBaseObject_Type,           /* tp_base           */
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
  = { { "protect",     (PyCFunction)  FastGCProtector_protect,         METH_VARARGS,
        FAST_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction)  FastGCProtector_unprotect,       METH_VARARGS,
        FAST_GC_PROTECTOR_UNPROTECT_DOC },
      { NULL, NULL, 0, NULL } };

PyGetSetDef  FastGCProtector_properties[]
  = { { "num_protected_objects", (getter) FastGCProtector_get_num_protected_objects, NULL,
        FAST_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

PyTypeObject  FastGCProtector_Type
  = { PyObject_HEAD_INIT (NULL)
      0,                                             /* ob_size           */
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


/*- Static variables -----------------------------------------------*/

static PyObject * raise_not_implemented_exception;


/*- AbstractGCProtector type methods -------------------------------*/

static void
AbstractGCProtector_dealloc (PyObject *self)
{
  self->ob_type->tp_free (self);
}


static PyObject *
AbstractGCProtector_protect (PyObject *self, PyObject *arguments)
{
  return PyObject_CallFunction (raise_not_implemented_exception, "Os", self, "protect");
}


static PyObject *
AbstractGCProtector_unprotect (PyObject *self, PyObject *arguments)
{
  return PyObject_CallFunction (raise_not_implemented_exception, "Os", self, "unprotect");
}


static PyObject *
AbstractGCProtector_set_default (PyObject *null, PyObject *arguments)
{
  PyObject *new_protector;

  if (!PyArg_ParseTuple (arguments, "O!:notify.gc.AbstractGCProtector.set_default",
                         &AbstractGCProtector_Type, &new_protector))
    return NULL;

  PyDict_SetItemString (AbstractGCProtector_Type.tp_dict, "default", new_protector);

  Py_INCREF (Py_None);
  return Py_None;
}


/*- FastGCProtector type methods -----------------------------------*/

static PyObject *
FastGCProtector_new (void)
{
  FastGCProtector *protector = PyObject_New (FastGCProtector, &FastGCProtector_Type);

  FastGCProtector_init (protector, PyTuple_New (0), NULL);
  return (PyObject *) protector;
}


static int
FastGCProtector_init (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  static char* supported_keywords[] = { NULL };

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":FastGCProtector", supported_keywords))
    return -1;

  self->num_protected_objects = 0;
  return 0;
}


static void
FastGCProtector_dealloc (FastGCProtector *self)
{
  self->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
FastGCProtector_protect (FastGCProtector *self, PyObject *arguments)
{
  PyObject *object;

  if (!PyArg_ParseTuple (arguments, "O:notify.gc.FastGCProtector.protect", &object))
    return NULL;

  Py_INCREF (object);
  ++self->num_protected_objects;

  Py_INCREF (object);
  return object;
}


static PyObject *
FastGCProtector_unprotect (FastGCProtector *self, PyObject *arguments)
{
  PyObject *object;

  if (!PyArg_ParseTuple (arguments, "O:notify.gc.FastGCProtector.unprotect", &object))
    return NULL;

  Py_DECREF (object);
  --self->num_protected_objects;

  Py_INCREF (object);
  return object;
}


static PyObject *
FastGCProtector_get_num_protected_objects (FastGCProtector *self)
{
  return PyInt_FromLong (self->num_protected_objects);
}


/*- Module initialization ------------------------------------------*/

#define REGISTER_TYPE(dictionary, type, name)                           \
  do                                                                    \
    {                                                                   \
      type.ob_type  = &PyType_Type;                                     \
      type.tp_alloc = PyType_GenericAlloc;                              \
      type.tp_new   = PyType_GenericNew;                                \
      if (PyType_Ready (&type) == 0)                                    \
        PyDict_SetItemString (dictionary, name, (PyObject *) &type);    \
    }                                                                   \
  while (0)


DL_EXPORT (void)
initgc (void)
{
  PyObject *module;
  PyObject *dictionary;
  PyObject *utilities;
  PyObject *default_protector;

  module     = Py_InitModule ("notify.gc", NULL);
  dictionary = PyModule_GetDict (module);

  utilities                       = PyImport_ImportModule ("notify.utils");
  raise_not_implemented_exception = PyDict_GetItemString (PyModule_GetDict (utilities),
                                                          "raise_not_implemented_exception");

  REGISTER_TYPE (dictionary, AbstractGCProtector_Type, "AbstractGCProtector");
  REGISTER_TYPE (dictionary, FastGCProtector_Type,     "FastGCProtector");

  default_protector = FastGCProtector_new ();
  PyDict_SetItemString (AbstractGCProtector_Type.tp_dict, "default", default_protector);
  Py_DECREF (default_protector);

  PyModule_AddStringConstant (module, "__doc__", MODULE_DOC);
  PyModule_AddStringConstant (module, "__docformat__", "epytext en");
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
